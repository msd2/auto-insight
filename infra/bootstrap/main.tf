# infra/bootstrap — one-shot, LOCAL-STATE config: the Spaces bucket (+ access
# key) that the root config's S3-compatible backend stores its state in.
#
# ── The chicken-and-egg, spelled out ────────────────────────────────────────
# Remote state needs a bucket; Terraform can't store state in a bucket it is
# itself creating. So this mini-config keeps its own state LOCAL (a single
# bucket + key — losing this state is a nuisance, not a disaster; both
# resources are trivially re-importable). Its outputs feed the root backend.
#
# There is a second, sneakier egg: the DO provider's Spaces resources
# (digitalocean_spaces_bucket) authenticate with SPACES credentials (env
# SPACES_ACCESS_KEY_ID / SPACES_SECRET_ACCESS_KEY), while
# digitalocean_spaces_key is managed through the normal API token. The key
# therefore must exist before the bucket resource can even plan — a
# TWO-PHASE APPLY of this one config:
#
#   export DIGITALOCEAN_TOKEN=<api token>
#   terraform init
#   terraform apply -target=digitalocean_spaces_key.terraform_state
#   export SPACES_ACCESS_KEY_ID=$(terraform output -raw spaces_access_key_id)
#   export SPACES_SECRET_ACCESS_KEY=$(terraform output -raw spaces_secret_access_key)
#   terraform apply        # creates the bucket
#
# (digitalocean_spaces_key needs provider ≥ 2.37; pinned below. If it
# misbehaves on first contact, the no-console fallback is
# `doctl spaces keys create terraform-state --grants "bucket=;permission=fullaccess"`
# and delete the key resource here.)
#
# NOTE: Spaces is not available in lon1 (London) — object storage regions are
# a shorter list (ams3, fra1, nyc3, sfo3, sgp1, syd1, blr1). State living in
# ams3 while the app runs in lon1 is fine; state access is not latency-
# sensitive. TODO: Marc to confirm along with the main region choice.
#
# STATE CAVEAT (honest): the Spaces secret key is captured in this config's
# local state file AND in its outputs. Keep infra/bootstrap/terraform.tfstate
# off git (repo .gitignore must cover *.tfstate) and treat the directory as
# operator-local.
#
# `terraform validate` has NOT been run here (Terraform not installed in the
# authoring environment); the file parses with python-hcl2 only.

terraform {
  required_version = ">= 1.7"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.40" # digitalocean_spaces_key needs >= 2.37
    }
  }
  # No backend block: local state, deliberately (see header).
}

# Token via DIGITALOCEAN_TOKEN env var; Spaces creds (phase 2) via
# SPACES_ACCESS_KEY_ID / SPACES_SECRET_ACCESS_KEY env vars.
provider "digitalocean" {}

variable "spaces_region" {
  description = "Spaces region for the state bucket. lon1 has NO Spaces; ams3 is the nearest to London."
  type        = string
  default     = "ams3"
}

variable "state_bucket_name" {
  description = "Globally unique Spaces bucket name for Terraform state."
  type        = string
  default     = "autoinsight-terraform-state"
}

# Phase 1 (API-token auth): the Spaces access key the backend + bucket
# resource will use. fullaccess on all buckets ("" = every bucket) so it can
# create the state bucket itself.
resource "digitalocean_spaces_key" "terraform_state" {
  name = "autoinsight-terraform-state"

  grant {
    bucket     = ""
    permission = "fullaccess"
  }
}

# Phase 2 (Spaces-key auth, see header): the state bucket. Versioning gives
# cheap state-history recovery; the bucket is private by default.
resource "digitalocean_spaces_bucket" "terraform_state" {
  name   = var.state_bucket_name
  region = var.spaces_region
  acl    = "private"

  versioning {
    enabled = true
  }
}

output "state_bucket_name" {
  value = digitalocean_spaces_bucket.terraform_state.name
}

output "state_bucket_endpoint" {
  description = "Goes into the root config's backend `endpoints.s3`."
  value       = "https://${var.spaces_region}.digitaloceanspaces.com"
}

output "spaces_access_key_id" {
  description = "Export as AWS_ACCESS_KEY_ID for the root backend (s3-backend quirk: the names are AWS_*, the credentials are Spaces)."
  value       = digitalocean_spaces_key.terraform_state.access_key
}

output "spaces_secret_access_key" {
  description = "Export as AWS_SECRET_ACCESS_KEY for the root backend."
  value       = digitalocean_spaces_key.terraform_state.secret_key
  sensitive   = true
}
