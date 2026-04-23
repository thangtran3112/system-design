# Terraform EKS scaffold

This folder provisions EKS infrastructure for federated GraphQL deployment.

## What it creates

- VPC with public/private subnets
- EKS control plane + managed node group
- ECR repositories for:
  - `graphql-federation-users`
  - `graphql-federation-todos`
  - `graphql-federation-router`

## Usage

```bash
cd terraform-eks
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

After apply:

```bash
aws eks update-kubeconfig --name $(terraform output -raw cluster_name) --region <your-region>
kubectl get nodes
```
