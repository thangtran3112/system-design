# FastAPI + GraphQL on AWS Lambda + API Gateway — Learning Guide

Deploy the same FastAPI GraphQL app to **serverless** infrastructure using Lambda and API Gateway.
**You type everything yourself** — copy from snippets, edit, and learn by doing.

---

## Part 1: Understanding Lambda vs ECS

---

### Phase 1: Why Lambda?

> You already deployed to ECS Fargate (always-running containers). Lambda is the other end of the spectrum —
> your code only runs when a request arrives. No traffic = no cost.

**ECS Fargate vs Lambda — when to use each:**

| | ECS Fargate | Lambda |
|---|---|---|
| **Billing** | Per-second while tasks run | Per-millisecond, only during execution |
| **Idle cost** | Paying even with zero traffic | $0 when idle |
| **Cold start** | None (always running) | 500ms–3s on first request |
| **Max execution** | Unlimited | 15 minutes |
| **Scaling** | You configure desired count | Auto-scales per request (0→1000) |
| **Package size** | Unlimited (Docker image) | 250 MB zip / 10 GB Docker image |
| **Best for** | Steady traffic, long-running | Spiky traffic, APIs, webhooks |

> **For a learning/side project**, Lambda is almost free. ECS Fargate minimum cost is ~$10/month
> even with zero traffic (1 task × 0.25 vCPU × 0.5 GB running 24/7).

---

### Phase 2: How FastAPI Runs on Lambda

> Lambda expects a `handler(event, context)` function. FastAPI is an ASGI app.
> **Mangum** bridges the two — it translates Lambda events into ASGI requests.

```
Without Mangum:
  Lambda event (JSON dict) → ??? → FastAPI doesn't understand this

With Mangum:
  Lambda event (JSON dict) → Mangum → ASGI request → FastAPI → ASGI response → Mangum → Lambda response
```

**The adapter is 3 lines of code:**

```python
from mangum import Mangum
from app.main import app

handler = Mangum(app)  # This is what Lambda calls
```

> **That's it.** Your entire FastAPI app — routes, GraphQL, middleware, auth — works unchanged.
> Mangum just translates the request format.

**Request flow through the full stack:**

```
┌──────────┐     ┌───────────────┐     ┌─────────────────────────────────┐
│  Client   │────▶│  API Gateway  │────▶│  Lambda                         │
│ (browser) │◀────│  (HTTP API)   │◀────│  handler(event, context)        │
└──────────┘     └───────────────┘     │    │                             │
                                       │    ▼                             │
                                       │  Mangum                          │
                                       │    │                             │
                                       │    ▼                             │
                                       │  FastAPI                         │
                                       │    ├── POST /graphql (Strawberry)│
                                       │    ├── GET  /health              │
                                       │    └── GET  /auth/google/login   │
                                       └─────────────────────────────────┘
```

---

### Phase 3: API Gateway — HTTP API vs REST API

> AWS has two types of API Gateway. For Lambda + FastAPI, always pick **HTTP API**.

| | HTTP API | REST API |
|---|---|---|
| **Cost** | $1.00 per million requests | $3.50 per million requests |
| **Latency** | Lower | Higher |
| **Features** | JWT auth, CORS, catch-all routes | WAF, API keys, usage plans, caching |
| **Lambda proxy** | ✅ Automatic | ✅ Automatic |
| **Best for** | Most APIs, microservices | APIs needing WAF or API key management |

> **HTTP API** is cheaper, faster, and has everything you need. REST API is the older, heavier option
> with features most apps don't need.

**The catch-all route pattern:**

```
API Gateway route:  ANY /{proxy+}    →   Lambda function
                    GET /             →   Lambda function  (root path)
```

> `{proxy+}` is a greedy path variable. It captures `/graphql`, `/health`, `/auth/google/login` —
> everything. API Gateway passes the full path to Lambda, and Mangum routes it to the right FastAPI endpoint.

---

## Part 2: Python Packaging for Lambda

---

### Phase 4: The Packaging Problem

> In JavaScript, `esbuild` bundles Express/Hono into a single file with tree-shaking.
> Python doesn't have an equivalent — here's why and what you do instead.

**Why Python can't tree-shake like JavaScript:**

```javascript
// JS: Static imports — bundler knows at build time what's used
import { Router } from 'express'    // bundler can trace this
```

```python
# Python: Dynamic imports — anything can happen at runtime
module = __import__(name)            # module name is a variable!
getattr(module, func_name)()         # function name is a variable!
```

> Python resolves imports at runtime, not build time. A bundler can't safely remove
> "unused" code because any module might be imported dynamically. This is a fundamental
> language difference, not a tooling gap.

**Packaging strategies ranked by Lambda suitability:**

| Strategy | Size | Cold Start | Complexity | Best For |
|---|---|---|---|---|
| **Zip + `--target`** | 20–60 MB | 1–3s | Low | Simple apps |
| **Lambda Layer** | Same, but shared | Slightly better | Medium | Multiple functions sharing deps |
| **Docker image** | 100–300 MB | 2–5s | Low | Large apps, native deps |
| **Stripped zip** | 10–30 MB | 0.5–1.5s | Medium | Production optimization |

---

### Phase 5: Building the Zip Package

> The simplest approach: install dependencies into a folder, add your code, zip it.

**Step 1: Install dependencies into a target directory:**

```bash
# Create a clean package directory
rm -rf package/
mkdir package/

# Install production deps only (no pytest, etc.)
# --target puts everything in ./package/ instead of site-packages
# --platform targets Lambda's OS (Amazon Linux)
pip install \
  --target ./package \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  fastapi uvicorn strawberry-graphql sqlalchemy mangum \
  httpx pydantic-settings python-jose
```

> **`--platform manylinux2014_x86_64`**: Lambda runs Amazon Linux. If you're building on macOS,
> any compiled C extensions (like `cryptography`) need to be built for Linux. This flag ensures
> pip downloads Linux-compatible wheels.
>
> **`--only-binary=:all:`**: Only download pre-built wheels, don't try to compile from source.
> This ensures you get Linux binaries even when building on macOS.

**Step 2: Create the Lambda handler:**

Create **`lambda_handler.py`** at the project root:

```python
from mangum import Mangum
from app.main import app

# Mangum wraps the ASGI app to handle Lambda events
# api_gateway_base_path="/" tells Mangum the API Gateway stage is at root
handler = Mangum(app, api_gateway_base_path="/")
```

> **Why a separate file?** Your `app/main.py` stays unchanged — it works for both
> `uvicorn` (local/ECS) and Lambda. The handler file is just the Lambda entry point.

**Step 3: Zip it all together:**

```bash
# Add dependencies
cd package && zip -r9 ../deploy.zip . && cd ..

# Add application code
zip -r9 deploy.zip app/ lambda_handler.py

# Check the size
ls -lh deploy.zip
# Should be ~20-40 MB for this app
```

> **Layer caching tip**: If you split into a Lambda Layer (dependencies) and function code (your app),
> you only re-upload the small function zip (~100 KB) on code changes. Dependencies rarely change.

---

### Phase 6: Trimming Package Size

> Every MB of package size adds cold start latency. Here's how to slim down.

**Remove unnecessary files from the package:**

```bash
# After pip install --target ./package, before zipping:

# Remove test directories (~5-10 MB savings)
find package/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null
find package/ -type d -name "test" -exec rm -rf {} + 2>/dev/null

# Remove __pycache__ (~2-5 MB savings)
find package/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove .dist-info metadata (~1-2 MB savings)
find package/ -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null

# Remove type stubs and py.typed markers
find package/ -name "*.pyi" -delete 2>/dev/null
find package/ -name "py.typed" -delete 2>/dev/null
```

**Size comparison:**

```
Before trimming:  ~45 MB
After trimming:   ~25 MB
Docker image:     ~250 MB (but Lambda handles image caching differently)
JS equivalent:    ~3 MB (esbuild tree-shaken Express app)
```

> **Why is Python so much bigger than JS?** Python packages include compiled `.so` files,
> type stubs, test suites, and metadata. JS bundles only include the code paths actually used.
> This is a real trade-off of the Python ecosystem.

---

### Phase 7: Docker Image for Lambda (Alternative)

> If your dependencies have native extensions or the zip exceeds 250 MB,
> use a Docker image instead. Lambda supports container images up to 10 GB.

Create **`dockerfile.lambda`**:

```dockerfile
# Use AWS's Lambda base image (includes Lambda runtime)
FROM public.ecr.aws/lambda/python:3.12

# Install uv for fast installs
RUN pip install uv

# Copy and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Install mangum (Lambda adapter)
RUN uv pip install --system mangum

# Copy application code
COPY app/ ./app/
COPY lambda_handler.py .

# Lambda calls this handler
CMD ["lambda_handler.handler"]
```

> **Key differences from your ECS Dockerfile:**
> - Base image: `public.ecr.aws/lambda/python:3.12` instead of `python:3.12-slim`
>   (includes Lambda Runtime Interface Client)
> - No `uvicorn` — Lambda manages the process lifecycle
> - No `EXPOSE` — Lambda networking is managed by AWS
> - `CMD` points to the handler function, not uvicorn

**Build and test locally:**

```bash
# Build the Lambda image
docker build -f dockerfile.lambda -t graphql-lambda .

# Run locally — Lambda images include a local emulator
docker run -p 9000:8080 graphql-lambda

# Test it (in another terminal)
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "requestContext": {"http": {"method": "POST", "path": "/graphql"}},
    "body": "{\"query\": \"{ todos { id title } }\"}",
    "headers": {"content-type": "application/json"},
    "isBase64Encoded": false
  }'
```

> The local emulator simulates the Lambda runtime. The event format matches
> what API Gateway HTTP API sends. This is how you debug locally before deploying.

---

## Part 3: Terraform — Lambda + API Gateway

---

### Phase 8: Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ AWS Account                                             │
│                                                         │
│  ┌─────────────┐      ┌──────────────┐                  │
│  │ API Gateway  │─────▶│   Lambda     │                  │
│  │ (HTTP API)   │◀─────│   Function   │                  │
│  │              │      │              │                  │
│  │ ANY /{proxy+}│      │ Mangum       │                  │
│  │ GET /        │      │  └─ FastAPI  │                  │
│  └──────┬──────┘      │     └─ GQL   │                  │
│         │              └──────┬───────┘                  │
│         │                     │                          │
│    Custom Domain         Reads secrets                   │
│    (optional)                 │                          │
│                        ┌──────▼───────┐                  │
│                        │   Secrets    │                  │
│                        │   Manager   │                  │
│                        └─────────────┘                  │
│                                                         │
│  ┌─────────────┐                                        │
│  │     ECR      │  (Docker image, if using image deploy)│
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

> **Compared to your ECS setup**: no ALB, no ECS cluster, no task definitions, no security groups
> for tasks. API Gateway replaces the ALB, and Lambda replaces ECS tasks.
> The infrastructure is significantly simpler.

---

### Phase 9: Terraform Project Structure

> We'll create a separate Terraform directory for Lambda deployment,
> keeping it independent from the ECS setup.

```
terraform-lambda/
├── main.tf                  # All resources
├── variables.tf             # Input variables
├── outputs.tf               # Output values
└── terraform.tfvars.example # Template for secrets
```

Create **`terraform-lambda/variables.tf`**:

```hcl
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for naming resources"
  type        = string
  default     = "graphql-todo-lambda"
}

# Secrets — pass via terraform.tfvars or TF_VAR_ env vars
# NEVER hardcode these

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "Secret key for signing app JWTs"
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "PostgreSQL connection string"
  type        = string
  sensitive   = true
}
```

> **Compared to ECS variables.tf**: no `container_port`, `desired_count`, `cpu`, or `memory`.
> Lambda manages all of that. You only configure what your app needs.

---

### Phase 10: Terraform — IAM Role for Lambda

> Lambda needs an **execution role** — permission to run and access AWS services.

Start **`terraform-lambda/main.tf`**:

```hcl
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ─────────────────────────────────────────────
# IAM — Lambda execution role
# ─────────────────────────────────────────────

# "Who can assume this role?" → Lambda service
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach AWS managed policy for basic Lambda permissions
# (CloudWatch Logs: create log group, put log events)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
```

> **ECS vs Lambda IAM comparison:**
> - ECS needs `AmazonECSTaskExecutionRolePolicy` (pull images, read secrets, write logs)
> - Lambda needs `AWSLambdaBasicExecutionRole` (just write logs)
> - Both need custom policies for Secrets Manager access

---

### Phase 11: Terraform — Secrets Manager + Lambda Permissions

```hcl
# ─────────────────────────────────────────────
# Secrets Manager — same secrets as ECS setup
# ─────────────────────────────────────────────

resource "aws_secretsmanager_secret" "google_client_secret" {
  name = "${var.project_name}/google-client-secret"
}

resource "aws_secretsmanager_secret_version" "google_client_secret" {
  secret_id     = aws_secretsmanager_secret.google_client_secret.id
  secret_string = var.google_client_secret
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name = "${var.project_name}/jwt-secret"
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/database-url"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = var.database_url
}

# Allow Lambda to read secrets
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${var.project_name}-secrets"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.google_client_secret.arn,
        aws_secretsmanager_secret.jwt_secret.arn,
        aws_secretsmanager_secret.database_url.arn,
      ]
    }]
  })
}
```

> **Key difference from ECS**: In ECS, secrets are injected as environment variables
> by the container agent (the `secrets` block in the task definition). In Lambda,
> your code reads them at runtime using the AWS SDK (`boto3`).
>
> You'd add this to your FastAPI config:
> ```python
> import boto3
> def get_secret(name):
>     client = boto3.client("secretsmanager")
>     return client.get_secret_value(SecretId=name)["SecretString"]
> ```

---

### Phase 12: Terraform — ECR + Lambda Function

```hcl
# ─────────────────────────────────────────────
# ECR — Docker image registry (for image-based Lambda)
# ─────────────────────────────────────────────

resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ─────────────────────────────────────────────
# CloudWatch Logs
# ─────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 30
}

# ─────────────────────────────────────────────
# Lambda Function
# ─────────────────────────────────────────────

resource "aws_lambda_function" "app" {
  function_name = var.project_name
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"                              # Using Docker image
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  timeout       = 30                                   # seconds
  memory_size   = 512                                  # MB

  environment {
    variables = {
      GOOGLE_CLIENT_ID = var.google_client_id
      # Sensitive values: read from Secrets Manager in code
      # Non-sensitive values can go here as env vars
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic,
  ]
}
```

> **Lambda configuration explained:**
> - **`package_type = "Image"`**: We're deploying a Docker image (not a zip file).
>   Change to `"Zip"` and use `filename` + `handler` for zip deployment.
> - **`timeout = 30`**: Max execution time per request. GraphQL queries should finish
>   well under this. Default is 3 seconds (too short for DB queries).
> - **`memory_size = 512`**: Lambda allocates CPU proportionally to memory.
>   512 MB ≈ 0.5 vCPU. More memory = faster cold starts too.
>
> **Cost at 512 MB memory:**
> ```
> 1 million requests/month × 200ms avg = $1.67
> Compare to ECS Fargate: ~$10/month minimum (even idle)
> ```

---

### Phase 13: Terraform — API Gateway HTTP API

```hcl
# ─────────────────────────────────────────────
# API Gateway — HTTP API (v2)
# ─────────────────────────────────────────────

resource "aws_apigatewayv2_api" "app" {
  name          = var.project_name
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["http://localhost:3000"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 3600
  }
}

# Connect API Gateway to Lambda
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.app.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"     # Use v2 event format (simpler)
}

# Catch-all route: ANY request → Lambda
resource "aws_apigatewayv2_route" "catch_all" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Root path route (API Gateway doesn't include / in {proxy+})
resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Deploy stage (auto-deploy on changes)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.lambda.arn
    format = jsonencode({
      requestId    = "$context.requestId"
      ip           = "$context.identity.sourceIp"
      method       = "$context.httpMethod"
      path         = "$context.path"
      status       = "$context.status"
      latency      = "$context.responseLatency"
    })
  }
}

# Allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.app.execution_arn}/*/*"
}
```

> **Breaking this down:**
>
> 1. **`aws_apigatewayv2_api`** — Creates the HTTP API. CORS is configured here
>    (not in FastAPI middleware — API Gateway handles it before Lambda is invoked).
>
> 2. **`aws_apigatewayv2_integration`** — Connects API Gateway to Lambda.
>    `AWS_PROXY` means API Gateway passes the raw HTTP request to Lambda and returns
>    the raw response. Your app has full control.
>    `payload_format_version = "2.0"` uses the simpler event format (Mangum supports both).
>
> 3. **Two routes** — `ANY /{proxy+}` catches all paths except root. `GET /` handles root.
>    API Gateway requires both because `{proxy+}` won't match an empty path.
>
> 4. **`aws_apigatewayv2_stage`** — The deployment stage. `$default` is the default stage
>    (no path prefix). `auto_deploy = true` means changes apply immediately.
>
> 5. **`aws_lambda_permission`** — Without this, API Gateway gets "access denied" when
>    calling Lambda. This is a **resource-based policy** on the Lambda function.

---

### Phase 14: Terraform — Outputs

Create **`terraform-lambda/outputs.tf`**:

```hcl
output "api_url" {
  description = "API Gateway URL — your app's public endpoint"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.app.function_name
}

output "ecr_repository_url" {
  description = "ECR repo URL — push Docker images here"
  value       = aws_ecr_repository.app.repository_url
}

output "graphql_endpoint" {
  description = "GraphQL endpoint URL"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/graphql"
}
```

Create **`terraform-lambda/terraform.tfvars.example`**:

```hcl
# Copy to terraform.tfvars and fill in real values
# NEVER commit terraform.tfvars — it contains secrets

aws_region   = "us-east-1"
project_name = "graphql-todo-lambda"

# OAuth
google_client_id     = "your-google-client-id.apps.googleusercontent.com"
google_client_secret = "your-google-client-secret"

# App
jwt_secret   = "a-strong-random-secret-change-this"
database_url = "postgresql://user:password@your-rds-hostname:5432/graphql_todos"
```

---

## Part 4: Deploy

---

### Phase 15: Build, Push, Deploy

**Step 1: Create the Lambda handler file:**

```bash
# In project root
cat > lambda_handler.py << 'EOF'
from mangum import Mangum
from app.main import app

handler = Mangum(app, api_gateway_base_path="/")
EOF
```

**Step 2: Build and push the Docker image:**

```bash
# Build the Lambda image
docker build -f dockerfile.lambda -t graphql-lambda .

# Initialize Terraform and create ECR
cd terraform-lambda
terraform init
terraform apply -target=aws_ecr_repository.app

# Get the ECR URL from output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin "$ECR_URL"

# Tag and push
docker tag graphql-lambda:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"
```

**Step 3: Deploy everything:**

```bash
# Plan — review what Terraform will create
terraform plan

# Apply — create all resources
terraform apply
```

> Terraform creates: IAM role, secrets, ECR repo, Lambda function, API Gateway,
> CloudWatch logs, and all the permissions connecting them.

**Step 4: Test it:**

```bash
# Get the API URL
API_URL=$(terraform output -raw api_url)

# Health check
curl "$API_URL/health"
# {"status": "ok"}

# GraphQL query
curl -X POST "$API_URL/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ todos { id title completed } }"}'
```

---

### Phase 16: Updating Your Code

```bash
# 1. Rebuild the image
docker build -f dockerfile.lambda -t graphql-lambda .

# 2. Push to ECR
docker tag graphql-lambda:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

# 3. Tell Lambda to use the new image
aws lambda update-function-code \
  --function-name graphql-todo-lambda \
  --image-uri "$ECR_URL:latest"
```

> **No Terraform needed for code updates.** Terraform manages infrastructure.
> `aws lambda update-function-code` just swaps the image. Same pattern as
> `aws ecs update-service --force-new-deployment` for ECS.

---

## Part 5: Lambda Concepts Deep Dive

---

### Phase 17: Cold Starts Explained

> The biggest trade-off with Lambda. Understanding it helps you optimize.

```
First request (cold start):
  [Download image] → [Start container] → [Init Python] → [Import app] → [Handle request]
  |←————————— 1-3 seconds ——————————→|                    |←— 50ms —→|

Subsequent requests (warm):
  [Handle request]
  |←— 50ms —→|
```

> Lambda keeps the container alive for **5–15 minutes** after the last request.
> During that window, requests are "warm" (fast). After that, the next request
> triggers a new cold start.

**What affects cold start time:**

| Factor | Impact | Your App |
|---|---|---|
| Package size | Bigger = slower download | ~250 MB Docker image → ~2s |
| Runtime | Python is moderate | ~500ms for Python init |
| Import time | Heavy imports = slower | SQLAlchemy + Strawberry ~300ms |
| Memory setting | More memory = more CPU = faster | 512 MB is good default |
| VPC | Adds ENI creation time | +1-2s if in VPC |

**Optimization strategies:**

```python
# lambda_handler.py — optimize imports

# These run ONCE during cold start (init phase)
# Lambda keeps them in memory for warm invocations
from mangum import Mangum
from app.main import app

handler = Mangum(app, api_gateway_base_path="/")

# DB connections created here persist across warm invocations
# This is GOOD — reuse connections instead of creating new ones per request
```

> **Provisioned Concurrency** keeps N containers permanently warm (eliminates cold starts)
> but costs more — like a middle ground between Lambda and Fargate.

---

### Phase 18: Lambda vs ECS — Full Comparison

> Now that you've seen both, here's the complete picture.

```
                     Lambda                              ECS Fargate
                  ┌──────────┐                       ┌──────────────┐
                  │ API GW   │                       │     ALB      │
                  │ (HTTP)   │                       │              │
                  └────┬─────┘                       └──────┬───────┘
                       │                                    │
                  ┌────▼─────┐                       ┌──────▼───────┐
                  │  Lambda  │                       │  ECS Service │
                  │ (0-1000) │                       │  (N tasks)   │
                  └──────────┘                       └──────────────┘

Infra resources:     ~8                                  ~15
Terraform lines:     ~150                                ~250
Scaling:           Automatic                     Manual (desired_count)
Min cost:          $0/month                       ~$10/month
```

| Aspect | Lambda + API Gateway | ECS Fargate + ALB |
|---|---|---|
| **Infrastructure** | API Gateway + Lambda + IAM | ALB + ECS cluster + task def + service + SGs + IAM |
| **Networking** | Managed by AWS | You configure VPC, subnets, security groups |
| **Scaling** | Per-request, 0 to 1000 concurrent | You set desired count, optional auto-scaling |
| **Cold starts** | Yes (1-3s) | No (always running) |
| **Max request duration** | 30s (API Gateway limit) | Unlimited |
| **WebSockets** | Requires separate WebSocket API | Native support |
| **Long-running tasks** | No (15 min max) | Yes |
| **Cost at 0 requests** | $0 | ~$10/month |
| **Cost at 1M requests** | ~$2/month | ~$10/month (same) |
| **Cost at 100M requests** | ~$200/month | ~$30/month (wins) |
| **GraphQL subscriptions** | Not straightforward | Works with WebSocket |
| **Best for your app** | Learning, low traffic, MVP | Production with steady traffic |

> **Rule of thumb**: Start with Lambda. Move to ECS when you need WebSockets,
> long-running requests, or your traffic is steady enough that always-on is cheaper.

---

### Phase 19: Summary

**What you learned:**

| Concept | What It Does |
|---|---|
| **Mangum** | Adapts ASGI (FastAPI) to Lambda's event format |
| **API Gateway HTTP API** | Routes HTTP requests to Lambda, handles CORS |
| **`{proxy+}`** | Catch-all route — sends all paths to one Lambda |
| **`AWS_PROXY` integration** | Passes raw HTTP to Lambda (vs transforming it) |
| **`payload_format_version 2.0`** | Simpler event format for HTTP APIs |
| **Lambda execution role** | IAM permissions for the function |
| **`aws_lambda_permission`** | Resource policy letting API Gateway invoke Lambda |
| **Cold start** | One-time init cost when Lambda spins up a new container |
| **Docker image Lambda** | Alternative to zip — uses ECR, supports larger packages |
| **`pip --target`** | Installs packages into a directory for zip packaging |
| **No Python tree-shaking** | Dynamic imports prevent JS-style bundling |
