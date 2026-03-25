output "cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "users_ecr_repository_url" {
  description = "Users image ECR repo URL"
  value       = aws_ecr_repository.users.repository_url
}

output "todos_ecr_repository_url" {
  description = "Todos image ECR repo URL"
  value       = aws_ecr_repository.todos.repository_url
}

output "router_ecr_repository_url" {
  description = "Router image ECR repo URL"
  value       = aws_ecr_repository.router.repository_url
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.aws_region}"
}
