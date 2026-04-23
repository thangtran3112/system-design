from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Google Auth directly with custom JWT signing
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30

    # Cognito settings
    cognito_domain: str = ""         # e.g., "your-app.auth.us-east-1.amazoncognito.com"
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    cognito_redirect_uri: str = "http://localhost:8000/auth/cognito/callback"
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: str = ""

    class Config:
        env_file = ".env"

settings = Settings()