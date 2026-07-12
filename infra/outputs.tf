output "ecr_repository_url" {
  description = "Push target for CI (docker build/push)."
  value       = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "github_deploy_role_arn" {
  description = "Set as GitHub environment secret AWS_ROLE_ARN (staging environment)."
  value       = aws_iam_role.github_deploy.arn
}

output "db_endpoint" {
  description = "RDS endpoint — used to compose the database-url secret at bootstrap."
  value       = aws_db_instance.main.address
}

output "db_master_user_secret_arn" {
  description = "RDS-managed master credentials secret (source for composing DATABASE_URL)."
  value       = one(aws_db_instance.main.master_user_secret[*].secret_arn)
}

output "app_security_group_id" {
  description = "For the one-off migration task's --network-configuration in CI."
  value       = aws_security_group.app.id
}

output "subnet_ids" {
  description = "For the one-off migration task's --network-configuration in CI."
  value       = data.aws_subnets.default.ids
}
