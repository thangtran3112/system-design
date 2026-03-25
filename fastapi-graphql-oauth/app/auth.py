import base64
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx
import jwt
from jwt import PyJWKClient
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.database import SessionLocal
from app.models import User

router = APIRouter(prefix="/auth")

@router.get("/google/login")
def google_login():
    """User clicks "Login with Google" → we redirect them to Google."""
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code"          # We want an authorization CODE
        "&scope=openid email profile"  # What data we want access to
        "&access_type=offline"         # Also give us a refresh_token
        "&prompt=consent"              # Always show consent screen
    )
    return RedirectResponse(url=google_auth_url)

# ──────────────────────────────────────────────
# Step 2: Google redirects back here with ?code=xxx
# ──────────────────────────────────────────────
@router.get("/google/callback")
async def google_callback(code: str):
    """
    Google sends the user back here after login.
    The 'code' query param is the authorization code.
    We exchange it for tokens.
    """
    # Exchange authorization code for tokens (server-to-server, not visible to browser)
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

    tokens = token_response.json()
    # tokens = {
    #   "access_token": "ya29.xxx...",
    #   "refresh_token": "1//xxx...",
    #   "id_token": "eyJhbG...",       ← JWT with user info
    #   "expires_in": 3599,
    #   "token_type": "Bearer"
    # }

    # ──────────────────────────────────────────────
    # Step 3: Get user info from Google
    # ──────────────────────────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    google_user = userinfo_response.json()
    # google_user = {
    #   "id": "123456789",
    #   "email": "user@gmail.com",
    #   "name": "John Doe",
    #   "picture": "https://lh3.googleusercontent.com/..."
    # }

    # ──────────────────────────────────────────────
    # Step 4: Create or update user in our database
    # ──────────────────────────────────────────────
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == google_user["email"]).first()
        if not user:
            user = User(
                email=google_user["email"],
                name=google_user["name"],
                picture=google_user.get("picture"),
                provider="google",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # ──────────────────────────────────────────────
    # Step 5: Issue OUR OWN JWT for the session
    # ──────────────────────────────────────────────
    # We don't use Google's token for our API. We create our own.
    # This way our app isn't dependent on Google's token lifecycle.
    app_token = create_app_token(user_id=user.id, email=user.email)

    # In a real app, you'd set this as an HTTP-only cookie
    # or return it to the frontend to store.
    return {"access_token": app_token, "user": {"id": user.id, "name": user.name}}

def create_app_token(user_id: int, email: str) -> str:
    """Create a JWT token for our app's session."""
    payload = {
        "sub": str(user_id),       # subject — who this token is for
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": datetime.now(timezone.utc),  # issued at
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_app_token(token: str) -> dict:
    """Verify and decode our app's JWT."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.get("/cognito/login")
def cognito_login():
    """Redirect to Cognito's Hosted UI (which may show Google/Facebook buttons)."""
    state = secrets.token_urlsafe(32)
    cognito_url = (
        f"https://{settings.cognito_domain}/oauth2/authorize"
        f"?client_id={settings.cognito_client_id}"
        f"&redirect_uri={settings.cognito_redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        f"&state={state}"
    )
    response = RedirectResponse(url=cognito_url)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300)
    return response

@router.get("/cognito/callback")
async def cognito_callback(code: str, state: str, request: Request):
    # Verify state (same CSRF protection)
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for tokens — same pattern, different URLs
    # Cognito requires Basic auth header: base64(client_id:client_secret)
    credentials = base64.b64encode(
        f"{settings.cognito_client_id}:{settings.cognito_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.cognito_redirect_uri,
            },
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code")

    tokens = token_response.json()

    # Verify the Cognito id_token using public JWKS keys
    jwks_url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
        f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    jwk_client = PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(tokens["id_token"])
    id_token_payload = jwt.decode(
        tokens["id_token"],
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.cognito_client_id,
        issuer=f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}",
    )
    # id_token_payload = {
    #   "sub": "a1b2c3d4-xxxx-xxxx-xxxx",   ← Cognito user ID
    #   "email": "user@gmail.com",
    #   "name": "John Doe",
    #   "cognito:username": "google_123456",
    #   "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx"
    # }

    # Create/update user in our DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == id_token_payload["email"]).first()
        if not user:
            user = User(
                email=id_token_payload["email"],
                name=id_token_payload.get("name", ""),
                picture=id_token_payload.get("picture"),
                provider="cognito",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    finally:
        db.close()

    # Issue our own app JWT (same as Google flow)
    app_token = create_app_token(user_id=user.id, email=user.email)
    return {"access_token": app_token, "user": {"id": user.id, "name": user.name}}

@router.post("/auth/refresh")
async def refresh_token(request: Request):
    """Use a refresh token to get a new access token."""
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")

    # Exchange refresh_token for new tokens
    # Works with both Google and Cognito (different URLs, same pattern)
    credentials = base64.b64encode(
        f"{settings.cognito_client_id}:{settings.cognito_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{settings.cognito_domain}/oauth2/token",
            data={
                "grant_type": "refresh_token",  # ← different grant_type
                "refresh_token": refresh_token,
            },
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Refresh failed — user must re-login")

    tokens = response.json()
    # Note: Cognito does NOT return a new refresh_token here.
    # Google does. Behavior varies by provider.
    return {
        "access_token": tokens["access_token"],
        "expires_in": tokens["expires_in"],
    }