# Kubernetes manifests for GraphQL federation

These manifests deploy three workloads on EKS:

- `users` subgraph
- `todos` subgraph
- `router` (public entrypoint)

## Files

- `namespace.yaml`
- `configmap.yaml`
- `secrets.yaml`
- `users-deployment.yaml`, `users-service.yaml`, `users-hpa.yaml`
- `todos-deployment.yaml`, `todos-service.yaml`, `todos-hpa.yaml`
- `router-supergraph.graphql`
- `router-supergraph-configmap.yaml`
- `router-deployment.yaml`, `router-service.yaml`, `router-hpa.yaml`
- `ingress.yaml`

## Apply order

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/router-supergraph-configmap.yaml

kubectl apply -f k8s/users-deployment.yaml
kubectl apply -f k8s/users-service.yaml
kubectl apply -f k8s/todos-deployment.yaml
kubectl apply -f k8s/todos-service.yaml

kubectl apply -f k8s/router-deployment.yaml
kubectl apply -f k8s/router-service.yaml
kubectl apply -f k8s/ingress.yaml

kubectl apply -f k8s/users-hpa.yaml
kubectl apply -f k8s/todos-hpa.yaml
kubectl apply -f k8s/router-hpa.yaml
```

## Verify

```bash
kubectl get pods -n graphql-federation
kubectl get svc -n graphql-federation
kubectl get ingress -n graphql-federation
kubectl logs deploy/router -n graphql-federation
```

## Image placeholders

Update these image references before apply:

- `users-deployment.yaml` image
- `todos-deployment.yaml` image

Use ECR outputs from `terraform-eks` and prefer immutable tags (for example commit SHA).

## Supergraph updates

`router-supergraph-configmap.yaml` ships a static supergraph for in-cluster service URLs.
When subgraph schema changes, regenerate supergraph in CI and update this ConfigMap.
