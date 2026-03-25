# FastAPI + GraphQL on AWS EKS (Kubernetes) — Learning Guide

Deploy the same FastAPI GraphQL app to **Kubernetes** using Amazon EKS.
**You type everything yourself** — copy from snippets, edit, and learn by doing.

---

## Part 1: Understanding Kubernetes and EKS

---

### Phase 1: Why Kubernetes?

> You've already deployed to ECS Fargate (AWS-managed containers) and Lambda (serverless).
> Kubernetes is the industry standard for container orchestration — used by most large teams.
> Learning it makes you portable across AWS, GCP, Azure, and on-premises.

**ECS vs EKS — the core difference:**

```
ECS (what you already know):
  AWS-proprietary API → AWS manages scheduling → Your containers run

EKS (Kubernetes):
  Kubernetes API (open standard) → Kubernetes manages scheduling → Your containers run
```

> **ECS** is simpler. **Kubernetes** is more powerful and portable.
> The concepts map directly — here's the translation:

| ECS Concept | Kubernetes Equivalent | What It Does |
|---|---|---|
| Task Definition | Pod spec (in a Deployment) | Describes containers, CPU, memory, env vars |
| Task | Pod | One running instance of your containers |
| Service | Deployment + Service | Keeps N replicas running, handles networking |
| Cluster | Cluster | Group of machines running your workloads |
| Fargate | Fargate (same!) or managed nodes | Compute that runs your Pods |
| ALB | Ingress + ALB Ingress Controller | Routes external traffic to your app |
| Target Group | Service (ClusterIP/NodePort) | Internal load balancing to Pods |
| Task Execution Role | Service Account + IAM Role | Permissions for your containers |
| Secrets Manager env | Kubernetes Secret or External Secrets | Sensitive configuration |
| CloudWatch Logs | CloudWatch + Fluent Bit DaemonSet | Log collection |

---

### Phase 2: Kubernetes Core Concepts

> Kubernetes has more moving parts than ECS. Understanding these before writing YAML
> makes everything click.

**The hierarchy:**

```
Cluster
  └── Node (a machine — EC2 instance or Fargate)
       └── Pod (smallest deployable unit — one or more containers)
            └── Container (your Docker image)
```

**The key resources you'll create:**

```
┌─────────────────────────────────────────────────────────────┐
│ Kubernetes Cluster                                          │
│                                                             │
│  ┌──────────────────┐   ┌────────────────────────────────┐  │
│  │    Ingress        │   │  Deployment                    │  │
│  │  (routing rules)  │   │  ┌──────────┐  ┌──────────┐   │  │
│  │                   │──▶│  │  Pod      │  │  Pod      │   │  │
│  │  /graphql → svc   │   │  │ ┌──────┐ │  │ ┌──────┐ │   │  │
│  │  /health  → svc   │   │  │ │ app  │ │  │ │ app  │ │   │  │
│  └──────────────────┘   │  │ └──────┘ │  │ └──────┘ │   │  │
│           │              │  └──────────┘  └──────────┘   │  │
│           ▼              └────────────────────────────────┘  │
│  ┌──────────────────┐                    ▲                   │
│  │    Service        │───────────────────┘                   │
│  │  (load balancer   │   Distributes traffic                │
│  │   across Pods)    │   across all healthy Pods            │
│  └──────────────────┘                                       │
│                                                             │
│  ┌──────────────────┐   ┌──────────────────┐                │
│  │  ConfigMap        │   │  Secret           │                │
│  │  (non-sensitive   │   │  (sensitive        │                │
│  │   config)         │   │   config)          │                │
│  └──────────────────┘   └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

**What each resource does:**

```
Deployment    — "I want 2 replicas of my app, using this Docker image, with these env vars."
                Kubernetes ensures 2 Pods are always running. If one crashes, it restarts it.
                This is the equivalent of an ECS Service + Task Definition combined.

Pod           — The actual running container(s). You rarely create Pods directly —
                the Deployment manages them. Like an ECS Task.

Service       — Internal load balancer. Gives your Pods a stable DNS name
                (e.g., graphql-todo.default.svc.cluster.local) and distributes traffic.
                Like an ECS Service's service discovery + target group.

Ingress       — Routes external HTTP traffic to Services based on path/host rules.
                Creates an AWS ALB automatically (with the ALB Ingress Controller).
                Like the ALB + listener rules in your ECS setup.

ConfigMap     — Key-value config injected as env vars or files. Non-sensitive.
                Like ECS task definition `environment` block.

Secret        — Base64-encoded sensitive config. Like ECS `secrets` block
                referencing Secrets Manager.

Namespace     — Logical isolation within a cluster. Like separate AWS accounts
                but lighter. Default namespace is "default".
```

---

### Phase 3: How EKS Works

> EKS is Kubernetes where AWS manages the **control plane** (the brain).
> You manage the **data plane** (the machines that run your Pods).

```
┌─────────────────────────────────────────────────────┐
│ EKS Cluster                                         │
│                                                     │
│  ┌─────────────────────┐   AWS manages this         │
│  │   Control Plane      │   (API server, etcd,       │
│  │   (Kubernetes API)   │    scheduler, controllers) │
│  └──────────┬──────────┘                            │
│             │                                       │
│  ┌──────────▼──────────┐   You choose:              │
│  │    Data Plane        │                            │
│  │                      │   Option A: Managed Nodes  │
│  │  ┌────┐ ┌────┐      │     EC2 instances (you     │
│  │  │Node│ │Node│      │     pick size, AWS manages) │
│  │  │    │ │    │      │                            │
│  │  │Pod │ │Pod │      │   Option B: Fargate         │
│  │  │Pod │ │Pod │      │     Serverless (like ECS    │
│  │  └────┘ └────┘      │     Fargate, no nodes)      │
│  └─────────────────────┘                            │
└─────────────────────────────────────────────────────┘
```

**Data plane options:**

| | Managed Node Group | Fargate |
|---|---|---|
| **What you manage** | Pick instance type + count | Nothing |
| **Scaling** | Cluster Autoscaler / Karpenter | Per-Pod automatic |
| **Cost** | EC2 pricing (cheaper at scale) | Per-Pod pricing (like ECS Fargate) |
| **DaemonSets** | ✅ Yes (log collectors, etc.) | ❌ No |
| **Best for** | Production, cost optimization | Learning, simple workloads |

> For learning, **Fargate** is simpler — no nodes to manage. For production,
> **managed node groups** with Karpenter give you more control and lower cost.
> We'll use managed node groups in this guide to learn more concepts.

---

## Part 2: Tools Setup

---

### Phase 4: Install CLI Tools

> You need three tools to work with EKS.

```bash
# 1. kubectl — the Kubernetes CLI (talks to any Kubernetes cluster)
brew install kubectl

# 2. eksctl — AWS-specific tool for creating/managing EKS clusters
brew install eksctl

# 3. helm — Kubernetes package manager (installs pre-built charts)
brew install helm

# Verify
kubectl version --client
eksctl version
helm version
```

> **kubectl** is like the AWS CLI but for Kubernetes. It sends requests to the
> Kubernetes API server. It works with EKS, GKE, AKS, minikube — any Kubernetes cluster.
>
> **eksctl** is an AWS-specific tool that creates EKS clusters with sensible defaults.
> Without it, you'd need 20+ AWS API calls to set up a cluster.
>
> **helm** is like `apt`/`brew` for Kubernetes. Instead of writing 200 lines of YAML
> for the ALB controller, you `helm install` it in one command.

**The configuration file — kubeconfig:**

```bash
# After creating a cluster, this command configures kubectl to talk to it
aws eks update-kubeconfig --name graphql-todo --region us-east-1

# kubectl now knows where to send requests
# Config stored at ~/.kube/config
kubectl config current-context
# Output: arn:aws:eks:us-east-1:123456:cluster/graphql-todo
```

> **kubeconfig** maps cluster names to API server URLs and auth credentials.
> It's like an SSH config but for Kubernetes. You can switch between clusters
> with `kubectl config use-context <name>`.

---

## Part 3: Kubernetes Manifests (YAML)

---

### Phase 5: Project Structure

> Kubernetes resources are defined in YAML files called "manifests".
> We'll keep them in a `k8s/` directory.

```
fastapi-graphql-oauth/
├── app/                    # Your FastAPI code (unchanged)
├── terraform/              # ECS Fargate infra (existing)
├── terraform-lambda/       # Lambda infra (existing)
├── k8s/                    # Kubernetes manifests (NEW)
│   ├── namespace.yaml
│   ├── secrets.yaml        # Template only — real values via kubectl
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── dockerfile              # Same Dockerfile, works for K8s too
└── LEARN-EKS.md
```

> **Your existing Dockerfile works unchanged.** Kubernetes just needs a container image —
> it doesn't care how it was built. The same `dockerfile` works for ECS, Lambda (with
> a different base), and Kubernetes.

---

### Phase 6: Namespace

> Namespaces are like folders — they isolate resources logically within a cluster.

Create **`k8s/namespace.yaml`**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: graphql-todo
```

```bash
kubectl apply -f k8s/namespace.yaml
# namespace/graphql-todo created

kubectl get namespaces
# NAME            STATUS   AGE
# default         Active   10m
# graphql-todo    Active   5s
# kube-system     Active   10m    ← Kubernetes internal components
```

> Without a namespace, everything goes into `default`. Using a dedicated namespace
> means you can `kubectl delete namespace graphql-todo` to clean up everything at once.

---

### Phase 7: ConfigMap and Secret

> ConfigMap = non-sensitive config. Secret = sensitive config. Both are injected
> as environment variables into your Pods.

Create **`k8s/configmap.yaml`**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: graphql-todo-config
  namespace: graphql-todo
data:
  GOOGLE_REDIRECT_URI: "http://localhost:8000/auth/google/callback"
```

> **ConfigMap** is plain text stored in the Kubernetes API server (etcd).
> Anyone with cluster access can read it. Never put secrets here.

Create **`k8s/secrets.yaml`** (template — don't commit real values):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: graphql-todo-secrets
  namespace: graphql-todo
type: Opaque
data:
  # Values must be base64-encoded
  # echo -n "your-value" | base64
  GOOGLE_CLIENT_ID: <base64-encoded>
  GOOGLE_CLIENT_SECRET: <base64-encoded>
  JWT_SECRET: <base64-encoded>
  DATABASE_URL: <base64-encoded>
```

**Create secrets from the command line instead (safer — no file to accidentally commit):**

```bash
kubectl create secret generic graphql-todo-secrets \
  --namespace graphql-todo \
  --from-literal=GOOGLE_CLIENT_ID="your-client-id" \
  --from-literal=GOOGLE_CLIENT_SECRET="your-secret" \
  --from-literal=JWT_SECRET="your-jwt-secret" \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db"
```

> **Kubernetes Secrets are NOT encrypted by default** — they're just base64-encoded
> (anyone can decode them). For production, enable encryption at rest or use
> **External Secrets Operator** to pull from AWS Secrets Manager:
>
> ```
> Without External Secrets:
>   You → kubectl create secret → stored in etcd (base64)
>
> With External Secrets:
>   ExternalSecret resource → reads from AWS Secrets Manager → creates K8s Secret
>   (Single source of truth stays in AWS, auto-synced)
> ```

---

### Phase 8: Deployment

> The Deployment is the core resource — it describes what to run and how many copies.
> This replaces both the ECS Task Definition and ECS Service.

Create **`k8s/deployment.yaml`**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graphql-todo
  namespace: graphql-todo
  labels:
    app: graphql-todo
spec:
  replicas: 2                          # Like ECS desired_count
  selector:
    matchLabels:
      app: graphql-todo                # "manage Pods with this label"
  template:                            # Pod template — what each replica looks like
    metadata:
      labels:
        app: graphql-todo              # Pods get this label
    spec:
      containers:
        - name: graphql-todo
          image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:latest
          ports:
            - containerPort: 8000      # Like ECS portMappings

          # Non-sensitive env vars from ConfigMap
          envFrom:
            - configMapRef:
                name: graphql-todo-config

          # Sensitive env vars from Secret
          env:
            - name: GOOGLE_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: graphql-todo-secrets
                  key: GOOGLE_CLIENT_ID
            - name: GOOGLE_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: graphql-todo-secrets
                  key: GOOGLE_CLIENT_SECRET
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: graphql-todo-secrets
                  key: JWT_SECRET
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: graphql-todo-secrets
                  key: DATABASE_URL

          # Resource limits — like ECS cpu/memory
          resources:
            requests:                  # Minimum guaranteed
              cpu: "250m"              # 250 millicores = 0.25 vCPU
              memory: "256Mi"
            limits:                    # Maximum allowed
              cpu: "500m"
              memory: "512Mi"

          # Health checks — like ECS healthCheck
          readinessProbe:              # "Is this Pod ready to receive traffic?"
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:               # "Is this Pod still alive?"
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
```

> **Key differences from ECS Task Definition:**
>
> - **`replicas: 2`** — In ECS, the Service has `desired_count`. In K8s, the Deployment has `replicas`.
> - **`selector.matchLabels`** — Kubernetes uses labels to connect resources. The Deployment
>   manages Pods matching `app: graphql-todo`. The Service routes to the same label.
> - **`requests` vs `limits`** — ECS has one CPU/memory value. Kubernetes has two:
>   - `requests`: guaranteed minimum (used for scheduling — "find a node with this much free")
>   - `limits`: hard cap (container is killed if it exceeds memory limit)
> - **Two health checks** — ECS has one `healthCheck`. Kubernetes has two:
>   - `readinessProbe`: Failed = stop sending traffic (Pod is temporarily unhealthy)
>   - `livenessProbe`: Failed = restart the Pod (Pod is permanently broken)

**Understanding labels and selectors:**

```
Deployment (selector: app=graphql-todo)
    │
    │ "I manage Pods with label app=graphql-todo"
    │
    ├── Pod (labels: app=graphql-todo)  ✅ managed
    ├── Pod (labels: app=graphql-todo)  ✅ managed
    └── Pod (labels: app=other-app)     ❌ not mine

Service (selector: app=graphql-todo)
    │
    │ "I route traffic to Pods with label app=graphql-todo"
    │
    └── Same Pods as above
```

> Labels are just key-value tags. They're how Kubernetes resources find each other.
> This is more flexible than ECS, where the Service and Task Definition are directly linked.

---

### Phase 9: Service

> A Service gives your Pods a stable network identity and load balances across them.
> In ECS, the Service + target group does this. In Kubernetes, it's a separate resource.

Create **`k8s/service.yaml`**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: graphql-todo
  namespace: graphql-todo
spec:
  type: ClusterIP                      # Internal only — Ingress handles external
  selector:
    app: graphql-todo                  # Route to Pods with this label
  ports:
    - port: 80                         # Service listens on 80
      targetPort: 8000                 # Forwards to container port 8000
      protocol: TCP
```

> **Service types:**
>
> | Type | What It Does | ECS Equivalent |
> |---|---|---|
> | `ClusterIP` | Internal only, reachable within cluster | Service discovery |
> | `NodePort` | Opens a port on every node | — |
> | `LoadBalancer` | Creates an AWS NLB/CLB directly | ALB (but less configurable) |
>
> We use `ClusterIP` because the **Ingress** will handle external traffic and create
> the ALB. Using `LoadBalancer` type would create a separate load balancer per Service
> (expensive if you have multiple services).

**How traffic flows:**

```
External request
    │
    ▼
Ingress (ALB) ──── "path /graphql → Service graphql-todo"
    │
    ▼
Service (ClusterIP) ──── round-robin across Pods
    │
    ├──▶ Pod 1 (10.0.1.5:8000)
    └──▶ Pod 2 (10.0.2.8:8000)
```

---

### Phase 10: Ingress

> Ingress defines routing rules for external HTTP traffic. With the AWS Load Balancer
> Controller, it automatically creates and configures an ALB.

Create **`k8s/ingress.yaml`**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: graphql-todo
  namespace: graphql-todo
  annotations:
    # Tell AWS LB Controller to create an ALB
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}]'
spec:
  ingressClassName: alb                # Use AWS ALB Ingress Controller
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: graphql-todo     # Route to our Service
                port:
                  number: 80
```

> **Annotations** are metadata that controllers read. `alb.ingress.kubernetes.io/*`
> annotations tell the AWS Load Balancer Controller how to configure the ALB.
> This is Kubernetes' extension mechanism — the core API is generic, annotations
> add provider-specific behavior.
>
> **Compared to your ECS Terraform**: In ECS, you wrote `aws_lb`, `aws_lb_target_group`,
> `aws_lb_listener`, and security groups — about 40 lines of Terraform.
> In Kubernetes, the Ingress controller creates all of that from 20 lines of YAML.

---

## Part 4: Terraform — EKS Cluster

---

### Phase 11: EKS Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ AWS Account                                                         │
│                                                                     │
│  ┌─────────────┐                                                    │
│  │ ECR          │  (same as ECS — your Docker image lives here)     │
│  └──────┬──────┘                                                    │
│         │                                                           │
│  ┌──────▼──────────────────────────────────────────────────────┐    │
│  │ EKS Cluster                                                  │    │
│  │                                                               │    │
│  │  ┌──────────────────┐     ┌────────────────────────────────┐ │    │
│  │  │ Control Plane     │     │ Node Group (2× t3.medium)      │ │    │
│  │  │ (AWS managed)     │     │                                │ │    │
│  │  │ API server        │────▶│  Node 1         Node 2         │ │    │
│  │  │ etcd              │     │  ┌─────────┐   ┌─────────┐    │ │    │
│  │  │ scheduler         │     │  │ Pod(app) │   │ Pod(app) │    │ │    │
│  │  └──────────────────┘     │  │ Pod(LBC) │   │ Pod(FB)  │    │ │    │
│  │                            │  └─────────┘   └─────────┘    │ │    │
│  │  LBC = ALB Load Balancer   └────────────────────────────────┘ │    │
│  │        Controller                                             │    │
│  │  FB  = Fluent Bit (logs)                                      │    │
│  └──────────────────────────────────────────────────────────────┘    │
│         │                                                           │
│  ┌──────▼──────┐                                                    │
│  │ ALB          │  (created by Ingress controller, not Terraform)   │
│  │ (internet)   │                                                    │
│  └─────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

> **Key difference from ECS Terraform**: In ECS, you created the ALB in Terraform.
> In EKS, the ALB Load Balancer Controller (running inside the cluster) creates the ALB
> when you apply the Ingress YAML. Terraform creates the cluster; kubectl creates the app resources.

---

### Phase 12: Terraform Project Structure

```
terraform-eks/
├── main.tf                  # VPC, EKS cluster, node group
├── variables.tf             # Input variables
├── outputs.tf               # Cluster endpoint, kubectl config command
└── terraform.tfvars.example # Template
```

Create **`terraform-eks/variables.tf`**:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "graphql-todo"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "node_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_count" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_min_count" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}
```

> **No secrets in EKS Terraform.** Unlike ECS/Lambda, we don't create Secrets Manager
> resources here. Secrets are managed in Kubernetes directly (`kubectl create secret`).
> In production you'd use External Secrets Operator to sync from AWS Secrets Manager.

---

### Phase 13: Terraform — VPC

> EKS needs a proper VPC with public and private subnets. Your ECS setup used the
> default VPC. EKS best practice is a dedicated VPC with tagged subnets.

Start **`terraform-eks/main.tf`**:

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
# Data — availability zones
# ─────────────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

# ─────────────────────────────────────────────
# VPC — dedicated network for EKS
# ─────────────────────────────────────────────
#
# Why not the default VPC? EKS needs:
# 1. Subnets tagged for Kubernetes (so the LB controller finds them)
# 2. Private subnets for worker nodes (security best practice)
# 3. NAT Gateway for private subnets to reach internet (pull images, etc.)

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway — allows public subnets to reach the internet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-igw" }
}

# ─── Public Subnets (for ALB) ────────────────

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"    # 10.0.1.0/24, 10.0.2.0/24
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${local.azs[count.index]}"
    # These tags are REQUIRED — the ALB controller uses them to find subnets
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${var.project_name}"    = "shared"
  }
}

# Public route table — traffic goes through Internet Gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ─── NAT Gateway (for private subnet internet access) ────

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${var.project_name}-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id    # NAT GW lives in a public subnet

  tags = { Name = "${var.project_name}-nat" }

  depends_on = [aws_internet_gateway.main]
}

# ─── Private Subnets (for worker nodes) ──────

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"   # 10.0.10.0/24, 10.0.11.0/24
  availability_zone = local.azs[count.index]

  tags = {
    Name = "${var.project_name}-private-${local.azs[count.index]}"
    # Tag for internal load balancers (if needed)
    "kubernetes.io/role/internal-elb"              = "1"
    "kubernetes.io/cluster/${var.project_name}"     = "shared"
  }
}

# Private route table — traffic goes through NAT Gateway
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = { Name = "${var.project_name}-private-rt" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
```

> **VPC layout visualized:**
>
> ```
> VPC 10.0.0.0/16
> ├── Public Subnet 10.0.1.0/24  (AZ-a) ── ALB, NAT Gateway
> ├── Public Subnet 10.0.2.0/24  (AZ-b) ── ALB
> ├── Private Subnet 10.0.10.0/24 (AZ-a) ── Worker nodes
> └── Private Subnet 10.0.11.0/24 (AZ-b) ── Worker nodes
> ```
>
> **Why public AND private subnets?**
> - ALB must be in public subnets (internet-facing)
> - Worker nodes go in private subnets (not directly reachable from internet)
> - NAT Gateway lets private nodes pull Docker images and talk to AWS APIs
>
> **The `kubernetes.io/role/elb` tag** is critical. The ALB controller scans for subnets
> with this tag when creating load balancers. Without it, `kubectl apply -f ingress.yaml`
> silently fails to create the ALB.

---

### Phase 14: Terraform — EKS Cluster

```hcl
# ─────────────────────────────────────────────
# IAM — EKS Cluster Role
# ─────────────────────────────────────────────
# The EKS service needs permissions to manage AWS resources on your behalf

resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-eks-cluster"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# ─────────────────────────────────────────────
# EKS Cluster
# ─────────────────────────────────────────────

resource "aws_eks_cluster" "main" {
  name     = var.project_name
  version  = var.cluster_version
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids = concat(
      aws_subnet.public[*].id,
      aws_subnet.private[*].id
    )
    endpoint_public_access  = true     # kubectl works from your laptop
    endpoint_private_access = true     # nodes talk to API server privately
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}
```

> **EKS cluster creation takes ~10 minutes.** This creates the Kubernetes control plane
> (API server, etcd, scheduler) — all managed by AWS. You don't see or pay for the
> control plane EC2 instances, but there's a flat $0.10/hour (~$73/month) cluster fee.

---

### Phase 15: Terraform — Node Group

```hcl
# ─────────────────────────────────────────────
# IAM — Node Group Role
# ─────────────────────────────────────────────
# Worker nodes need permissions to join the cluster, pull images, etc.

resource "aws_iam_role" "eks_nodes" {
  name = "${var.project_name}-eks-nodes"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Three managed policies every node group needs
resource "aws_iam_role_policy_attachment" "eks_worker_node" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ─────────────────────────────────────────────
# EKS Managed Node Group
# ─────────────────────────────────────────────

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = aws_subnet.private[*].id     # Nodes in private subnets

  instance_types = [var.node_instance_type]

  scaling_config {
    desired_size = var.node_desired_count
    min_size     = var.node_min_count
    max_size     = var.node_max_count
  }

  # Ensure IAM policies are attached before creating nodes
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_read,
  ]
}
```

> **The three node IAM policies explained:**
>
> | Policy | Why |
> |---|---|
> | `AmazonEKSWorkerNodePolicy` | Join the EKS cluster, register as a node |
> | `AmazonEKS_CNI_Policy` | Manage network interfaces (each Pod gets its own IP) |
> | `AmazonEC2ContainerRegistryReadOnly` | Pull Docker images from ECR |
>
> **In ECS**: one `AmazonECSTaskExecutionRolePolicy` covers all of this.
> Kubernetes is more granular because each component (kubelet, CNI plugin, etc.)
> has distinct responsibilities.

---

### Phase 16: Terraform — ECR + Outputs

```hcl
# ─────────────────────────────────────────────
# ECR — Docker image registry (same as ECS setup)
# ─────────────────────────────────────────────

resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}
```

Create **`terraform-eks/outputs.tf`**:

```hcl
output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "ecr_repository_url" {
  description = "ECR repo URL — push Docker images here"
  value       = aws_ecr_repository.app.repository_url
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.aws_region}"
}
```

Create **`terraform-eks/terraform.tfvars.example`**:

```hcl
# Copy to terraform.tfvars and fill in values

aws_region          = "us-east-1"
project_name        = "graphql-todo"
cluster_version     = "1.29"
node_instance_type  = "t3.medium"
node_desired_count  = 2
```

---

## Part 5: Deploy

---

### Phase 17: Create the Cluster

```bash
cd terraform-eks

# Initialize Terraform
terraform init

# Review the plan
terraform plan
# You'll see: VPC, subnets, IGW, NAT GW, EKS cluster, node group, ECR
# ~20 resources

# Create everything (~15 minutes — EKS cluster creation is slow)
terraform apply
```

> **Cost warning**: EKS is the most expensive option for learning:
> - EKS control plane: $0.10/hour ($73/month)
> - 2× t3.medium nodes: ~$0.042/hour each ($60/month)
> - NAT Gateway: $0.045/hour + data ($33/month)
> - **Total: ~$166/month** (vs $10 ECS Fargate, $0 Lambda)
>
> **Destroy when done learning**: `terraform destroy`

---

### Phase 18: Configure kubectl and Install ALB Controller

```bash
# Configure kubectl to talk to your cluster
aws eks update-kubeconfig --name graphql-todo --region us-east-1

# Verify connection
kubectl get nodes
# NAME                          STATUS   ROLES    AGE   VERSION
# ip-10-0-10-45.ec2.internal    Ready    <none>   5m    v1.29.x
# ip-10-0-11-78.ec2.internal    Ready    <none>   5m    v1.29.x
```

**Install the AWS Load Balancer Controller (creates ALBs from Ingress resources):**

```bash
# Add the EKS Helm chart repo
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Install the controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system \
  --set clusterName=graphql-todo \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller

# Verify it's running
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
# NAME                                            READY   STATUS    RESTARTS   AGE
# aws-load-balancer-controller-xxxx-xxxxx          1/1     Running   0          30s
```

> **Why a separate install?** Kubernetes is modular. The core doesn't know about AWS ALBs.
> The Load Balancer Controller is an **addon** that watches for Ingress resources and
> creates/configures ALBs automatically. This is the "Kubernetes way" — small, composable pieces.
>
> **Note**: In production, the controller needs an IAM role via IRSA (IAM Roles for Service Accounts)
> to create ALBs. For learning, the node role's permissions are sufficient.

---

### Phase 19: Build, Push, Deploy

```bash
# 1. Build your Docker image (same Dockerfile as ECS)
docker build -t graphql-todo .

# 2. Get ECR URL
ECR_URL=$(cd terraform-eks && terraform output -raw ecr_repository_url)

# 3. Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin "$ECR_URL"

# 4. Tag and push
docker tag graphql-todo:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

# 5. Update the image in deployment.yaml
# Replace <ACCOUNT_ID>.dkr.ecr... with actual ECR URL in k8s/deployment.yaml

# 6. Apply all Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 7. Create secrets (from command line, not YAML file)
kubectl create secret generic graphql-todo-secrets \
  --namespace graphql-todo \
  --from-literal=GOOGLE_CLIENT_ID="your-client-id" \
  --from-literal=GOOGLE_CLIENT_SECRET="your-secret" \
  --from-literal=JWT_SECRET="your-jwt-secret" \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db"
```

---

### Phase 20: Verify and Debug

```bash
# Check Pods are running
kubectl get pods -n graphql-todo
# NAME                            READY   STATUS    RESTARTS   AGE
# graphql-todo-6b7d8f9c4-abc12    1/1     Running   0          1m
# graphql-todo-6b7d8f9c4-def34    1/1     Running   0          1m

# Check the Service
kubectl get svc -n graphql-todo
# NAME           TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
# graphql-todo   ClusterIP   172.20.45.67   <none>        80/TCP    1m

# Check the Ingress (wait 2-3 minutes for ALB creation)
kubectl get ingress -n graphql-todo
# NAME           CLASS   HOSTS   ADDRESS                                  PORTS   AGE
# graphql-todo   alb     *       k8s-graphql-xxxx.us-east-1.elb.amazonaws.com   80   3m

# Get the ALB URL
ALB_URL=$(kubectl get ingress -n graphql-todo graphql-todo -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test it
curl "http://$ALB_URL/health"
# {"status": "ok"}

curl -X POST "http://$ALB_URL/graphql" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ todos { id title } }"}'
```

**Debugging commands you'll use constantly:**

```bash
# View Pod logs (like CloudWatch but instant)
kubectl logs -n graphql-todo -l app=graphql-todo --tail=50

# Follow logs in real time
kubectl logs -n graphql-todo -l app=graphql-todo -f

# Describe a Pod (events, status, why it's failing)
kubectl describe pod -n graphql-todo <pod-name>

# Shell into a running Pod (like docker exec)
kubectl exec -it -n graphql-todo <pod-name> -- /bin/bash

# See events (scheduling failures, image pull errors, etc.)
kubectl get events -n graphql-todo --sort-by='.lastTimestamp'

# Port-forward to test locally (bypass ALB)
kubectl port-forward -n graphql-todo svc/graphql-todo 8000:80
# Now curl http://localhost:8000/health works
```

> **`kubectl port-forward`** is extremely useful. It tunnels traffic from your laptop
> directly to a Pod or Service, bypassing all external networking. Great for debugging
> whether the issue is your app or the networking/ALB configuration.

---

### Phase 21: Updating Your Code

```bash
# 1. Rebuild and push
docker build -t graphql-todo .
docker tag graphql-todo:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

# 2. Restart Pods to pull the new image
kubectl rollout restart deployment/graphql-todo -n graphql-todo

# 3. Watch the rollout
kubectl rollout status deployment/graphql-todo -n graphql-todo
# Waiting for deployment "graphql-todo" rollout to finish: 1 old replicas are pending termination...
# deployment "graphql-todo" successfully rolled out
```

> **Rolling update** — Kubernetes starts new Pods with the new image, waits for them
> to pass readiness checks, then terminates old Pods. Zero downtime.
> This is the same as ECS's rolling deployment, but you can see it happening in real time.

---

## Part 6: How Terraform and kubectl Work Together

---

### Phase 22: Two Tools, Two Jobs

> This is a common confusion: does Terraform use the k8s YAML files?
> **No.** They are completely independent workflows.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Deployment Pipeline                       │
│                                                                   │
│  Step 1: INFRASTRUCTURE (Terraform)                              │
│  ┌─────────────────────────────────────────────────────┐         │
│  │  terraform apply                                     │         │
│  │                                                       │         │
│  │  Creates:  VPC, subnets, EKS cluster, node group,   │         │
│  │            ECR, IAM roles                             │         │
│  │                                                       │         │
│  │  Reads:    terraform-eks/*.tf                         │         │
│  │  Ignores:  k8s/*.yaml  ← doesn't know about these   │         │
│  └─────────────────────────────────────────────────────┘         │
│                         │                                         │
│                         │ cluster exists now                      │
│                         ▼                                         │
│  Step 2: APPLICATION (kubectl)                                    │
│  ┌─────────────────────────────────────────────────────┐         │
│  │  kubectl apply -f k8s/                               │         │
│  │                                                       │         │
│  │  Creates:  Namespace, Deployment, Pods, Service,     │         │
│  │            Ingress, ConfigMap, Secrets                │         │
│  │                                                       │         │
│  │  Reads:    k8s/*.yaml                                 │         │
│  │  Ignores:  terraform-eks/*.tf  ← doesn't need these  │         │
│  └─────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

> **Think of it like building a house:**
> - Terraform = contractor who builds the house (foundation, walls, roof)
> - kubectl = interior designer who furnishes the house (furniture, appliances)
> - They work on the same house, but use different blueprints and different tools.

---

### Phase 23: Authenticating kubectl to AWS EKS

> When you run `kubectl get pods`, how does it know which cluster to talk to,
> and how does AWS know you're allowed?

**The authentication flow:**

```
kubectl get pods
    │
    ▼
~/.kube/config says:
    "For cluster 'graphql-todo', run `aws eks get-token` to authenticate"
    │
    ▼
AWS CLI uses your IAM credentials (from env vars, ~/.aws/credentials, or IAM role)
    │
    ▼
AWS returns a short-lived token (valid ~15 minutes)
    │
    ▼
kubectl sends that token to the EKS API server
    │
    ▼
EKS verifies the token against IAM → grants access
    │
    ▼
You see your Pods
```

**Setting up the connection:**

```bash
# This one command configures everything:
aws eks update-kubeconfig --name graphql-todo --region us-east-1

# It writes to ~/.kube/config, adding:
# - Cluster: API server URL + certificate
# - Auth:    "run aws eks get-token" for each request
# - Context: maps a friendly name to the cluster + auth
```

**The kubeconfig file explained:**

```yaml
# ~/.kube/config (simplified)
clusters:
  - name: graphql-todo
    cluster:
      server: https://ABCD1234.gr7.us-east-1.eks.amazonaws.com  # EKS API endpoint
      certificate-authority-data: LS0tLS1...                      # TLS cert

users:
  - name: graphql-todo-user
    user:
      exec:
        command: aws                        # Run AWS CLI
        args: ["eks", "get-token",          # to get a token
               "--cluster-name", "graphql-todo"]

contexts:
  - name: arn:aws:eks:us-east-1:123456:cluster/graphql-todo
    context:
      cluster: graphql-todo
      user: graphql-todo-user
```

> **Key insight**: kubectl doesn't store passwords or long-lived tokens.
> Every time you run a kubectl command, it calls `aws eks get-token` which
> uses your current IAM identity to generate a fresh, short-lived token.
>
> **Who has cluster access?** The IAM identity that ran `terraform apply`
> (created the cluster) is automatically the cluster admin. Other IAM
> users/roles need to be added to the `aws-auth` ConfigMap:
>
> ```bash
> # See who has access
> kubectl get configmap aws-auth -n kube-system -o yaml
>
> # The cluster creator is admin by default — not listed in aws-auth
> # but always has full access
> ```

**Both tools need AWS credentials, but for different reasons:**

| Tool | Uses AWS Credentials To... |
|---|---|
| `terraform` | Create/modify/destroy AWS resources (VPC, EKS, EC2, etc.) |
| `kubectl` | Authenticate to the EKS API server (via `aws eks get-token`) |
| `docker push` | Push images to ECR (via `aws ecr get-login-password`) |

> **All three tools use the same `~/.aws/credentials`** or environment variables.
> If `aws sts get-caller-identity` works, all three tools can authenticate.

---

## Part 7: Kubernetes Concepts Deep Dive

---

### Phase 24: How Kubernetes Keeps Your App Running

```
You: "I want 2 replicas"  (Deployment spec)
                │
                ▼
Kubernetes control loop (runs continuously):
                │
    ┌───────────┴───────────┐
    │ Desired state: 2 Pods │
    │ Current state: ???    │
    └───────────┬───────────┘
                │
    ┌───────────▼───────────┐
    │ 2 running? → do nothing│
    │ 1 running? → start 1   │
    │ 3 running? → stop 1    │
    │ 0 running? → start 2   │
    └───────────────────────┘
```

> This is **declarative** — you declare what you want, Kubernetes figures out how.
> Same philosophy as Terraform, but for running processes instead of cloud resources.
>
> **ECS works the same way** (desired count → scheduler ensures N tasks). The difference
> is Kubernetes exposes this pattern for everything: networking, storage, DNS, certificates, etc.

---

### Phase 25: Scaling

**Manual scaling:**

```bash
# Scale to 4 replicas
kubectl scale deployment/graphql-todo -n graphql-todo --replicas=4

# Scale to 1 (save money while testing)
kubectl scale deployment/graphql-todo -n graphql-todo --replicas=1
```

**Auto-scaling with HPA (Horizontal Pod Autoscaler):**

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: graphql-todo
  namespace: graphql-todo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: graphql-todo
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70     # Scale up when CPU > 70%
```

> **ECS equivalent**: ECS Application Auto Scaling with target tracking policy.
> Same concept, different API. Kubernetes HPA is more flexible — you can scale on
> custom metrics (requests per second, queue depth) not just CPU/memory.

---

### Phase 26: Full Comparison — ECS vs Lambda vs EKS

```
                Lambda              ECS Fargate           EKS
             ┌──────────┐       ┌──────────────┐    ┌──────────────┐
             │ API GW   │       │     ALB      │    │     ALB      │
             └────┬─────┘       └──────┬───────┘    └──────┬───────┘
                  │                    │                    │
             ┌────▼─────┐       ┌──────▼───────┐    ┌──────▼───────┐
             │  Lambda  │       │  ECS Service │    │  Deployment  │
             │ (0-1000) │       │  (N tasks)   │    │  (N Pods)    │
             └──────────┘       └──────────────┘    └──────────────┘

Infra:           ~8                  ~15                 ~20+
TF lines:        ~150                ~250                ~300
K8s YAML:        0                   0                   ~100
Setup time:      5 min               10 min              15 min
Cluster cost:    $0                  $0                  $73/month
Compute cost:    per-request         per-second          per-node
Min monthly:     $0                  ~$10                ~$166
```

| Aspect | Lambda | ECS Fargate | EKS |
|---|---|---|---|
| **Learning curve** | Lowest | Medium | Highest |
| **Infra complexity** | Simplest | Medium | Most complex |
| **Operational burden** | AWS handles everything | You manage service config | You manage cluster + apps |
| **Portability** | AWS-only | AWS-only (mostly) | Any cloud, on-premises |
| **Ecosystem** | Limited | AWS integrations | Massive (Helm charts, operators) |
| **Scaling** | Automatic per-request | Manual or auto-scaling | HPA, VPA, Karpenter |
| **Cold starts** | Yes (1-3s) | No | No |
| **WebSockets** | Requires separate API | Native | Native |
| **Multi-service** | Separate functions | Separate services | All in one cluster |
| **CI/CD** | Push image/zip | Push image, update service | Push image, kubectl apply |
| **Observability** | CloudWatch only | CloudWatch | Prometheus, Grafana, anything |
| **Cost at 0 req/s** | $0 | ~$10/month | ~$166/month |
| **Cost at 100 req/s** | ~$30/month | ~$15/month | ~$166/month (node cost fixed) |
| **Cost at 10K req/s** | ~$2,500/month | ~$100/month | ~$200/month |
| **Best for** | MVPs, low traffic | Small-medium production | Large teams, multi-service |

> **Rule of thumb:**
> - **Side project / MVP**: Lambda (free tier, zero maintenance)
> - **Small production app**: ECS Fargate (simple, cost-effective)
> - **Large team / many services**: EKS (portable, powerful, but complex)
> - **Already using Kubernetes elsewhere**: EKS (leverage existing knowledge)

---

### Phase 27: Clean Up

```bash
# 1. Delete Kubernetes resources first
kubectl delete namespace graphql-todo

# 2. Uninstall Helm charts
helm uninstall aws-load-balancer-controller -n kube-system

# 3. Destroy Terraform resources (~10 minutes)
cd terraform-eks
terraform destroy

# Verify nothing is left
aws eks list-clusters --region us-east-1
```

> **Always delete K8s resources before Terraform destroy.** If Terraform deletes the VPC
> while an ALB (created by the Ingress controller) still exists, Terraform gets stuck
> because the ALB holds references to the VPC subnets. Deleting the Ingress first
> lets the controller clean up the ALB.

---

### Phase 28: Summary

**What you learned:**

| Concept | What It Does |
|---|---|
| **EKS** | AWS-managed Kubernetes control plane |
| **Managed Node Group** | EC2 instances that auto-join the cluster |
| **Deployment** | Declares desired state (image, replicas, env vars, health checks) |
| **Pod** | Smallest deployable unit — one running instance of your containers |
| **Service (ClusterIP)** | Internal load balancer with stable DNS name |
| **Ingress** | External HTTP routing rules → creates ALB via controller |
| **ConfigMap** | Non-sensitive configuration as env vars |
| **Secret** | Sensitive configuration (base64, not encrypted by default) |
| **Namespace** | Logical isolation within a cluster |
| **Labels + Selectors** | How K8s resources find and connect to each other |
| **kubectl** | CLI for Kubernetes API (portable across any cluster) |
| **helm** | Package manager for Kubernetes (install complex apps in one command) |
| **ALB Controller** | Addon that creates AWS ALBs from Ingress resources |
| **readiness vs liveness** | "Stop traffic" vs "restart Pod" health checks |
| **requests vs limits** | Guaranteed minimum vs hard cap for CPU/memory |
| **Rolling update** | Zero-downtime deployment (new Pods up before old Pods down) |
| **port-forward** | Debug tunnel from laptop directly to Pod/Service |
| **HPA** | Auto-scales Pods based on CPU/memory/custom metrics |
| **Subnet tagging** | `kubernetes.io/role/elb` — how controllers discover AWS resources |
| **Terraform vs kubectl** | Independent tools — Terraform builds infra, kubectl deploys apps |
| **kubeconfig** | Maps cluster names to API endpoints + auth commands |
| **EKS auth flow** | kubectl → `aws eks get-token` → IAM token → EKS API server |
| **aws-auth ConfigMap** | Controls which IAM identities can access the cluster |
| **GitHub Actions CI/CD** | Automates build → push → terraform → kubectl pipeline |
| **OIDC federation** | GitHub Actions assumes AWS IAM role without storing secrets |
| **Terraform state backend** | S3 + DynamoDB for shared, locked remote state |

---

## Part 8: CI/CD with GitHub Actions

---

### Phase 29: Pipeline Architecture

> In production, you never run `terraform apply` or `kubectl apply` from your laptop.
> A CI/CD pipeline does it — triggered by git push.

```
git push to main
    │
    ▼
GitHub Actions workflow starts
    │
    ├── Job 1: INFRASTRUCTURE (runs only if terraform-eks/ changed)
    │   ├── terraform init
    │   ├── terraform plan
    │   └── terraform apply (auto-approve)
    │
    ├── Job 2: BUILD & PUSH (runs on every push)
    │   ├── docker build
    │   ├── docker tag
    │   └── docker push → ECR
    │
    └── Job 3: DEPLOY (runs after build)
        ├── aws eks update-kubeconfig
        ├── kubectl apply -f k8s/
        └── kubectl rollout status
```

> **Why separate jobs?**
> - Infrastructure changes are rare (new cluster, scaling config)
> - App deployments happen on every code change
> - Separating them means you don't re-run Terraform on every push
>
> **Key question: How does GitHub Actions authenticate to AWS?**
> You don't store `AWS_ACCESS_KEY_ID` as a GitHub secret (old way, risky).
> Instead, you use **OIDC federation** — GitHub proves its identity to AWS,
> and AWS grants a temporary role. No long-lived credentials anywhere.

```
Old way (avoid):
  Store AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY as GitHub secrets
  → Long-lived credentials → rotation burden → leak risk

New way (OIDC):
  GitHub Actions  ──proves identity──▶  AWS IAM
                  ◀──temporary token──  (valid 1 hour)
  → No stored secrets → automatic rotation → scoped to repo
```

---

### Phase 30: AWS Setup for GitHub Actions

> Before writing the workflow, you need an IAM role that GitHub Actions can assume.

**1. Create an OIDC provider (one-time per AWS account):**

```hcl
# Add to terraform-eks/main.tf (or a separate ci.tf)

# OIDC provider — lets GitHub Actions prove its identity to AWS
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# If the provider doesn't exist yet, create it:
# resource "aws_iam_openid_connect_provider" "github" {
#   url             = "https://token.actions.githubusercontent.com"
#   client_id_list  = ["sts.amazonaws.com"]
#   thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
# }
```

**2. Create an IAM role for GitHub Actions:**

```hcl
resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow this specific repo — not any GitHub repo
          "token.actions.githubusercontent.com:sub" = "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }]
  })
}

# Attach policies the pipeline needs
resource "aws_iam_role_policy_attachment" "github_ecr" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

resource "aws_iam_role_policy_attachment" "github_eks" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}
```

> **The `Condition` block is critical.** Without it, any GitHub repo in the world
> could assume your IAM role. The `StringLike` condition restricts it to your specific repo.
>
> **Permissions explained:**
> - `AmazonEC2ContainerRegistryPowerUser` — push/pull Docker images to ECR
> - `AmazonEKSClusterPolicy` — interact with the EKS cluster
> - For Terraform, you'd need broader permissions (VPC, IAM, etc.) — often
>   a separate role with `AdministratorAccess` scoped to the infra job only

---

### Phase 31: Terraform Remote State

> When CI/CD runs `terraform apply`, it needs to know the current state.
> Local `terraform.tfstate` doesn't work — each pipeline run starts fresh.
> You need a **remote backend**.

```
Local state (your laptop):
  terraform.tfstate lives on disk → only you can run terraform

Remote state (S3 + DynamoDB):
  terraform.tfstate lives in S3 → anyone/any pipeline can run terraform
  DynamoDB lock table → prevents two applies at the same time
```

**Add to the top of `terraform-eks/main.tf`:**

```hcl
terraform {
  required_version = ">= 1.5"

  # Remote state — shared across team and CI/CD
  backend "s3" {
    bucket         = "graphql-todo-terraform-state"    # Create this bucket first
    key            = "eks/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"                 # Create this table first
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

> **Create the S3 bucket and DynamoDB table manually first** (chicken-and-egg problem —
> you can't use Terraform to create the backend that Terraform needs):
>
> ```bash
> # One-time setup
> aws s3api create-bucket --bucket graphql-todo-terraform-state --region us-east-1
> aws s3api put-bucket-versioning --bucket graphql-todo-terraform-state \
>   --versioning-configuration Status=Enabled
>
> aws dynamodb create-table \
>   --table-name terraform-locks \
>   --attribute-definitions AttributeName=LockID,AttributeType=S \
>   --key-schema AttributeName=LockID,KeyType=HASH \
>   --billing-mode PAY_PER_REQUEST
> ```
>
> **Why DynamoDB?** Two people (or two pipeline runs) running `terraform apply`
> at the same time would corrupt state. DynamoDB provides a lock — the second
> run waits until the first finishes.

---

### Phase 32: The GitHub Actions Workflow

Create **`.github/workflows/deploy.yml`**:

```yaml
name: Deploy to EKS

on:
  push:
    branches: [main]

# OIDC — GitHub Actions gets temporary AWS credentials
permissions:
  id-token: write    # Required for OIDC
  contents: read

env:
  AWS_REGION: us-east-1
  EKS_CLUSTER: graphql-todo
  ECR_REPO: graphql-todo

jobs:
  # ─────────────────────────────────────────
  # Job 1: Infrastructure (only when TF files change)
  # ─────────────────────────────────────────
  infrastructure:
    runs-on: ubuntu-latest
    # Only run if terraform files changed
    if: contains(github.event.head_commit.modified, 'terraform-eks/')
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/graphql-todo-github-actions
          aws-region: us-east-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        working-directory: terraform-eks
        run: terraform init

      - name: Terraform Plan
        working-directory: terraform-eks
        run: terraform plan -no-color

      - name: Terraform Apply
        working-directory: terraform-eks
        run: terraform apply -auto-approve -no-color

  # ─────────────────────────────────────────
  # Job 2: Build and push Docker image
  # ─────────────────────────────────────────
  build:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/graphql-todo-github-actions
          aws-region: us-east-1

      - name: Login to ECR
        id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image
        id: meta
        env:
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}       # Use git SHA as tag — unique per commit
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG .
          docker build -t $ECR_REGISTRY/$ECR_REPO:latest .
          docker push $ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPO:latest
          echo "tags=$ECR_REGISTRY/$ECR_REPO:$IMAGE_TAG" >> $GITHUB_OUTPUT

  # ─────────────────────────────────────────
  # Job 3: Deploy to Kubernetes
  # ─────────────────────────────────────────
  deploy:
    runs-on: ubuntu-latest
    needs: build                             # Wait for image to be pushed
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/graphql-todo-github-actions
          aws-region: us-east-1

      - name: Configure kubectl
        run: aws eks update-kubeconfig --name $EKS_CLUSTER --region $AWS_REGION

      - name: Apply manifests
        run: |
          kubectl apply -f k8s/namespace.yaml
          kubectl apply -f k8s/configmap.yaml
          kubectl apply -f k8s/deployment.yaml
          kubectl apply -f k8s/service.yaml
          kubectl apply -f k8s/ingress.yaml

      - name: Update image to new tag
        env:
          IMAGE: ${{ needs.build.outputs.image_tag }}
        run: |
          kubectl set image deployment/graphql-todo \
            graphql-todo=$IMAGE \
            -n graphql-todo

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/graphql-todo \
            -n graphql-todo --timeout=300s
```

> **How the workflow flows:**
>
> ```
> push to main
>     │
>     ├── infrastructure (if TF changed)
>     │     terraform plan → terraform apply
>     │
>     ├── build (always)
>     │     docker build → docker push to ECR
>     │     outputs: image tag (e.g., 123456.dkr.ecr....:abc123f)
>     │
>     └── deploy (after build completes)
>           kubectl apply -f k8s/  → apply manifests
>           kubectl set image      → update to new image tag
>           kubectl rollout status → wait until healthy
> ```

**Key details:**

| Line | Why |
|---|---|
| `permissions: id-token: write` | Required for OIDC — lets GitHub request a token from AWS |
| `role-to-assume` | The IAM role created in Phase 30 — no secrets stored |
| `github.sha` as image tag | Every commit gets a unique image — enables rollbacks |
| `kubectl set image` | Updates the Deployment to use the new image tag |
| `needs: build` | Deploy waits for the image to be pushed before proceeding |
| `--timeout=300s` | Fail the pipeline if rollout takes more than 5 minutes |

---

### Phase 33: Pipeline Variations

**Option A: Separate infra and app repos (common in larger teams):**

```
repo: infrastructure          repo: graphql-todo-app
├── terraform-eks/            ├── app/
├── terraform/                ├── k8s/
└── .github/workflows/       ├── dockerfile
    └── infra.yml             └── .github/workflows/
                                  └── deploy.yml

Infrastructure team manages    App team manages
Terraform changes              code + K8s manifests
```

**Option B: GitOps with ArgoCD (advanced):**

```
Traditional (what we built):
  GitHub Actions → kubectl apply → cluster updated

GitOps (ArgoCD):
  GitHub Actions → push image + update k8s/ YAML → git push
  ArgoCD (running in cluster) → watches git repo → auto-applies changes

Difference:
  Traditional: pipeline pushes TO the cluster
  GitOps:      cluster pulls FROM git
```

> **ArgoCD** is popular for production EKS because:
> - Git is the single source of truth — `git log` shows every deployment
> - Automatic drift detection — if someone runs `kubectl edit`, ArgoCD reverts it
> - Multi-cluster — one ArgoCD instance can deploy to many clusters
>
> For a learning project, the direct `kubectl apply` approach is simpler and sufficient.

**Option C: Environment promotion (staging → production):**

```yaml
# deploy.yml — different behavior per branch
on:
  push:
    branches:
      - main        # → deploy to staging
      - production  # → deploy to production

jobs:
  deploy:
    environment: ${{ github.ref == 'refs/heads/production' && 'production' || 'staging' }}
    # GitHub Environments can require manual approval for production
```

---

### Phase 34: Summary — The Full Picture

```
Developer                  GitHub                        AWS
─────────                  ──────                        ───

git push ──────────▶ Actions workflow starts
                         │
                         ├── OIDC ──────────────▶ IAM verifies GitHub identity
                         │ ◀──────────────────── temporary credentials
                         │
                         ├── terraform apply ───▶ Creates/updates EKS + VPC + ECR
                         │
                         ├── docker build + push ▶ Image stored in ECR
                         │
                         ├── kubectl apply ─────▶ Manifests applied to cluster
                         │
                         ├── kubectl set image ──▶ Deployment updated to new tag
                         │
                         └── rollout status ────▶ Waits for healthy Pods
                                                      │
                                                      ▼
                                                  Users hit ALB → Pods serve traffic
```

---

## Part 9: Progressive Delivery + Operations Notes (EKS)

---

### Phase 35: Viewing Logs and Entering a Pod

> In Kubernetes, you usually do **not** SSH/login to a Pod just to see logs.
> You use `kubectl logs` directly.

```bash
# 1) List pods
kubectl get pods -n graphql-todo

# 2) View logs from one pod
kubectl logs -n graphql-todo <pod-name>

# 3) Follow logs in real time
kubectl logs -n graphql-todo -f <pod-name>

# 4) If pod has multiple containers
kubectl logs -n graphql-todo <pod-name> -c <container-name>

# 5) Previous container logs (after restart/crash)
kubectl logs -n graphql-todo <pod-name> --previous
```

**Only for debugging internals (files/processes), enter the container shell:**

```bash
kubectl exec -it -n graphql-todo <pod-name> -- /bin/sh
# or /bin/bash if your image includes bash
```

> For production, centralize logs to CloudWatch (for example via Fluent Bit) so
> you can query logs across all Pods and restarts in one place.

---

### Phase 36: ECS CodeDeploy vs Kubernetes Blue/Green + Canary

> In ECS, CodeDeploy provides blue/green and canary orchestration.
> In Kubernetes, this is usually done by **controllers + traffic routing**.

| ECS / CodeDeploy | Kubernetes / EKS Equivalent |
|---|---|
| Blue/Green deployment | Argo Rollouts BlueGreen strategy |
| Canary deployment | Argo Rollouts Canary strategy |
| Target group traffic shift | Ingress/service mesh weighted routing |
| Deployment lifecycle hooks | Rollout steps, pauses, analysis |

**What this means operationally:**

- **Blue/Green**: Keep active and preview versions, then switch traffic when ready.
- **Canary**: Shift traffic in percentages (for example 10% → 30% → 60% → 100%).
- **Rollback**: Abort/pause promotion if health checks or metrics degrade.

---

### Phase 37: Do You Need to Install Argo and HPA?

Short answer: **yes, some components must be installed.**

- **HPA resource** is built into Kubernetes API, but needs metrics to function.
- **Metrics Server** is required for CPU/memory autoscaling.
- **Argo Rollouts** is not built into Kubernetes; install its controller.
- **AWS Load Balancer Controller** is required for ALB Ingress traffic routing.

```bash
# Quick checks
kubectl top nodes                              # verifies metrics pipeline
kubectl get pods -n argo-rollouts             # verifies Argo controller
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

---

### Phase 38: Install Argo Rollouts (Local Laptop)

> Works for local clusters (kind, minikube, Docker Desktop Kubernetes).

```bash
# Install Argo Rollouts controller
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Install kubectl plugin (Linux)
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x kubectl-argo-rollouts-linux-amd64
sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# Verify
kubectl argo rollouts version
kubectl -n argo-rollouts get deploy
```

If HPA metrics are missing locally:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl top nodes
```

---

### Phase 39: Install Argo Rollouts (AWS EKS)

```bash
# 1) Connect kubectl to EKS
aws eks update-kubeconfig --region us-east-1 --name graphql-todo

# 2) Install Argo Rollouts
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# 3) Verify
kubectl -n argo-rollouts get pods
kubectl argo rollouts version
```

> For EKS, also ensure:
> - `metrics-server` is available (`kubectl top nodes` works)
> - AWS Load Balancer Controller is installed for ALB Ingress routing

---

### Phase 40: Manifests in This Repository (Canary + Blue/Green + HPA)

> This project now includes Argo Rollouts manifests under:

```
k8s/argo-rollouts/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── canary/
│   ├── services.yaml
│   ├── ingress.yaml
│   ├── rollout.yaml
│   └── hpa.yaml
└── bluegreen/
    ├── services.yaml
    ├── ingress.yaml
    ├── rollout.yaml
    └── hpa.yaml
```

**Apply order:**

```bash
# Shared resources first
kubectl apply -f k8s/argo-rollouts/namespace.yaml
kubectl apply -f k8s/argo-rollouts/configmap.yaml
kubectl apply -f k8s/argo-rollouts/secrets.yaml

# Then pick ONE strategy
kubectl apply -f k8s/argo-rollouts/canary
# or
kubectl apply -f k8s/argo-rollouts/bluegreen
```

> Run either canary or blue/green for the same app at a time to avoid routing conflicts.
