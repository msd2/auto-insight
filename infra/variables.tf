variable "aws_region" {
  description = "AWS region for all resources. TODO: confirm with Marc (eu-west-2 assumed — Culture Counts UK pilot; SES + RDS both available)."
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name (staging | production). One root module, one state file / tfvars per environment — see envs/."
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Resource name prefix."
  type        = string
  default     = "autoinsight"
}

variable "github_repository" {
  description = "GitHub owner/repo allowed to assume the deploy role via OIDC."
  type        = string
  default     = "msd2/auto-insight"
}

# ── Database ────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class. Pilot-sized; bump per environment via tfvars."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage in GiB."
  type        = number
  default     = 20
}

variable "db_name" {
  type    = string
  default = "autoinsight"
}

variable "db_username" {
  type    = string
  default = "autoinsight"
}

# ── Runtime (ECS Fargate) ───────────────────────────────────────────────────

variable "image_tag" {
  description = "Image tag both services run. CI pushes :staging and :<sha>; pin to a sha for production promotes (README §Promote)."
  type        = string
  default     = "staging"
}

variable "api_cpu" {
  type    = number
  default = 256 # 0.25 vCPU
}

variable "api_memory" {
  type    = number
  default = 512 # MiB
}

variable "worker_cpu" {
  type    = number
  default = 256
}

variable "worker_memory" {
  type    = number
  default = 512
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "worker_desired_count" {
  description = "Exactly 1 for the pilot. Procrastinate handles concurrent workers safely (Postgres locking), so this can scale later."
  type        = number
  default     = 1
}
