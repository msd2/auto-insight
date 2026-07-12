# Postgres 16 on RDS — one instance per environment, app data + Procrastinate
# job queue in the same database (per docs/02-architecture.md).

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_security_group" "db" {
  name_prefix = "${var.project}-${var.environment}-db-"
  description = "Postgres, reachable only from the app tasks"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from api/worker tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "main" {
  identifier        = "${var.project}-${var.environment}"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage

  db_name  = var.db_name
  username = var.db_username
  # RDS generates and stores the master password in Secrets Manager for us —
  # no password ever passes through Terraform state or CI.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  storage_encrypted       = true
  backup_retention_period = 7
  apply_immediately       = true

  # Staging posture. For production set deletion_protection = true,
  # skip_final_snapshot = false (+ final_snapshot_identifier) via tfvars-driven
  # locals or per-env overrides — flagged in README.md §Promote.
  deletion_protection = false
  skip_final_snapshot = true
}

# NOTE: the application DATABASE_URL
# (postgresql+asyncpg://user:pass@endpoint:5432/dbname) is composed from the
# RDS-managed master secret + aws_db_instance.main.address and written into
# aws_secretsmanager_secret.database_url (secrets.tf) as a manual bootstrap
# step after first apply — see README.md §Bootstrap.
