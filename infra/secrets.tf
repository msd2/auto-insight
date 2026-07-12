# Application secrets — Secrets Manager for anything injected into task
# definitions, SSM Parameter Store reserved for non-secret config.
#
# Convention:
#   Secrets Manager  ${project}/${environment}/<kebab-name>   (secret values)
#   SSM parameters   /${project}/${environment}/<kebab-name>  (plain config)
#
# Only the secret *containers* are managed here; VALUES are set out-of-band
# (console or `aws secretsmanager put-secret-value`) so nothing sensitive
# transits Terraform state. See README.md §Bootstrap for the fill-in list.

resource "aws_secretsmanager_secret" "database_url" {
  name        = "${var.project}/${var.environment}/database-url"
  description = "Full SQLAlchemy DATABASE_URL (postgresql+asyncpg://...) composed from the RDS endpoint + master credentials after first apply."
}

# TODO(phase-0.3+): app session/signing secret once WP 0.3 auth lands —
# uncomment and add to both task definitions' `secrets` lists.
# resource "aws_secretsmanager_secret" "app_secret_key" {
#   name = "${var.project}/${var.environment}/app-secret-key"
# }

# TODO(phase-1): Spektrix per-org credentials live in the DATABASE
# (box_office_connections.credentials, encrypted at rest) — NOT here. Only the
# application-level encryption key for that column belongs in Secrets Manager:
# resource "aws_secretsmanager_secret" "credentials_encryption_key" {
#   name = "${var.project}/${var.environment}/credentials-encryption-key"
# }

# TODO(phase-5): Claude API key for insight generation.
# resource "aws_secretsmanager_secret" "anthropic_api_key" {
#   name = "${var.project}/${var.environment}/anthropic-api-key"
# }
