# Terraform + provider version pins.
#
# NOTE: no DigitalOcean account exists yet (WP 0.4 authoring). Nothing here
# has been applied; `terraform init`/`validate` need network access to fetch
# the provider but no credentials.

terraform {
  required_version = ">= 1.7"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.40"
    }
  }

  # Remote state backend — COMMENTED OUT until the DO account exists.
  # DigitalOcean has no native Terraform backend; the standard approach is a
  # DO Spaces bucket via the s3-compatible backend (the skip_* flags disable
  # AWS-specific validation the backend would otherwise attempt).
  #
  # The bucket + Spaces key are THEMSELVES Terraform-managed, by the one-shot
  # local-state config in infra/bootstrap/ (see its header for the
  # chicken-and-egg). Wiring, per README.md §Bootstrap:
  #   bucket    = bootstrap output `state_bucket_name`
  #   endpoints = bootstrap output `state_bucket_endpoint`
  #   creds     = bootstrap outputs `spaces_access_key_id` /
  #               `spaces_secret_access_key`, exported as
  #               AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (s3-backend quirk:
  #               AWS_* names, Spaces credentials)
  # then uncomment and `terraform init -migrate-state`. Until then Terraform
  # falls back to harmless local state — fine, nothing exists to manage yet.
  #
  # NOTE: Spaces has no lon1 region — the bucket lives in ams3 (state access
  # is not latency-sensitive; see infra/bootstrap/main.tf).
  #
  # backend "s3" {
  #   bucket = "autoinsight-terraform-state"       # = bootstrap state_bucket_name
  #   key    = "staging/terraform.tfstate"         # per-environment key
  #   region = "us-east-1"                         # dummy; required by the backend, ignored by Spaces
  #   endpoints = {
  #     s3 = "https://ams3.digitaloceanspaces.com" # = bootstrap state_bucket_endpoint
  #   }
  #   skip_credentials_validation = true
  #   skip_requesting_account_id  = true
  #   skip_metadata_api_check     = true
  #   skip_region_validation      = true
  #   skip_s3_checksum            = true
  #   use_path_style              = true
  # }
}
