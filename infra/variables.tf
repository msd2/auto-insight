variable "region" {
  description = "DigitalOcean datacenter region for the database. TODO: lon1 (London) assumed — Marc to confirm. (The Terraform-state Spaces bucket lives in ams3 — Spaces has no lon1; see infra/bootstrap/.)"
  type        = string
  default     = "lon1"
}

variable "app_region" {
  description = "App Platform region slug. NOTE: App Platform uses short slugs (lon, ams, fra, nyc) — not the datacenter slugs (lon1) the database uses. Keep the two aligned."
  type        = string
  default     = "lon"
}

variable "environment" {
  description = "Environment name (staging | production). One root module, one state key / tfvars per environment — see envs/."
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Resource name prefix."
  type        = string
  default     = "autoinsight"
}

variable "github_repository" {
  description = "GitHub owner/repo App Platform builds from (requires the DigitalOcean GitHub app to be authorised for it — README §Unblocking)."
  type        = string
  default     = "msd2/auto-insight"
}

variable "github_branch" {
  description = "Branch App Platform tracks. main for staging; production tracks a release branch or gets promoted manually (README §Promote)."
  type        = string
  default     = "main"
}

variable "deploy_on_push" {
  description = "Native App Platform CD: rebuild + redeploy on every push to github_branch. true for staging (this IS the staging CD mechanism); false for production (manual promote only)."
  type        = bool
  default     = true
}

# ── DNS (all default-off so applies work before a domain exists) ───────────

variable "manage_dns" {
  description = "Create the app's DNS record + attach the custom domain to the app. Leave false until Marc provides a domain AND its nameservers are delegated to DigitalOcean (see dns.tf header)."
  type        = bool
  default     = false
}

variable "domain" {
  description = "Apex domain (e.g. autoinsight.example) once it exists. Only read when manage_dns = true."
  type        = string
  default     = ""
}

variable "create_domain_zone" {
  description = "Create the digitalocean_domain zone itself. true in exactly ONE environment (staging) — the zone is account-wide and the environments must not both claim it."
  type        = bool
  default     = false
}

variable "app_subdomain" {
  description = "Subdomain for the app hostname. Empty = the environment name (staging.<domain>); production sets app_subdomain = \"app\"."
  type        = string
  default     = ""
}

# ── Database ────────────────────────────────────────────────────────────────

variable "db_size" {
  description = "Managed Postgres node size. db-s-1vcpu-1gb ($15/mo) is the smallest tier."
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "db_node_count" {
  type    = number
  default = 1
}

variable "db_name" {
  type    = string
  default = "autoinsight"
}

# ── App Platform sizing ─────────────────────────────────────────────────────

variable "api_instance_size" {
  description = "App Platform instance slug. basic-xxs = 0.5 GiB / shared vCPU, $5/mo."
  type        = string
  default     = "basic-xxs"
}

variable "api_instance_count" {
  type    = number
  default = 1
}

variable "worker_instance_size" {
  type    = string
  default = "basic-xxs"
}

variable "worker_instance_count" {
  description = "Exactly 1 for the pilot. Procrastinate handles concurrent workers safely (Postgres locking), so this can scale later."
  type        = number
  default     = 1
}
