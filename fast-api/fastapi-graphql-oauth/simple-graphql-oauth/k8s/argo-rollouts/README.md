# Argo Rollouts + HPA manifests

This folder contains Kubernetes manifests for progressive delivery on EKS using Argo Rollouts.

## Prerequisites

- Argo Rollouts controller installed in the cluster.
- Metrics Server installed (required by HPA).
- AWS Load Balancer Controller installed (ALB ingress class).

## Layout

- `namespace.yaml`, `configmap.yaml`, `secrets.yaml`: shared resources.
- `canary/`: canary rollout with stable/canary services, ALB ingress, and HPA.
- `bluegreen/`: blue-green rollout with active/preview services, ALB ingress, and HPA.

## Deploy shared resources

```bash
kubectl apply -f k8s/argo-rollouts/namespace.yaml
kubectl apply -f k8s/argo-rollouts/configmap.yaml
kubectl apply -f k8s/argo-rollouts/secrets.yaml
```

## Deploy canary

```bash
kubectl apply -f k8s/argo-rollouts/canary
kubectl argo rollouts get rollout graphql-todo-canary -n graphql-todo --watch
```

## Deploy blue-green

```bash
kubectl apply -f k8s/argo-rollouts/bluegreen
kubectl argo rollouts get rollout graphql-todo-bluegreen -n graphql-todo --watch
```

## Notes

- Replace `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/graphql-todo:<tag>` with your ECR image.
- For production, create secrets with `kubectl create secret` instead of committing values.
- Canary and blue-green are alternatives. Run one strategy at a time for this app.
