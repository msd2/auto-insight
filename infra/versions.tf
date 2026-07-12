# Terraform + provider version pins.
#
# NOTE: no AWS account exists yet (Phase 0 authoring). Nothing here has been
# applied; `terraform init`/`validate` require network access to download the
# AWS provider but no credentials.

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state backend — COMMENTED OUT until the AWS account exists.
  # Bootstrap order (see README.md §Bootstrap):
  #   1. Create the state bucket + lock table manually (or with a tiny
  #      separate one-shot config) in the chosen account/region.
  #   2. Uncomment this block, adjust names, run `terraform init -migrate-state`.
  # Until then Terraform falls back to harmless local state, which is fine
  # because there is nothing to manage yet.
  #
  # backend "s3" {
  #   bucket         = "autoinsight-terraform-state"   # TODO: must be globally unique
  #   key            = "staging/terraform.tfstate"     # per-environment key
  #   region         = "eu-west-2"                     # TODO: confirm region with Marc
  #   dynamodb_table = "autoinsight-terraform-locks"
  #   encrypt        = true
  # }
}
