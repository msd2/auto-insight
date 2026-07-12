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
  # Bootstrap order (see README.md §Bootstrap):
  #   1. Create a Spaces bucket + Spaces access key in the chosen region.
  #   2. Uncomment, adjust names, export AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
  #      to the Spaces key pair, run `terraform init -migrate-state`.
  # Until then Terraform falls back to harmless local state, which is fine
  # because there is nothing to manage yet.
  #
  # backend "s3" {
  #   bucket = "autoinsight-terraform-state"       # TODO: create in Spaces
  #   key    = "staging/terraform.tfstate"         # per-environment key
  #   region = "us-east-1"                         # dummy; required by the backend, ignored by Spaces
  #   endpoints = {
  #     s3 = "https://lon1.digitaloceanspaces.com" # TODO: confirm region with Marc
  #   }
  #   skip_credentials_validation = true
  #   skip_requesting_account_id  = true
  #   skip_metadata_api_check     = true
  #   skip_region_validation      = true
  #   skip_s3_checksum            = true
  #   use_path_style              = true
  # }
}
