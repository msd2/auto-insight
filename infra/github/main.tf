# infra/github — OPTIONAL mini-config: the GitHub-side wiring the deploy
# workflow needs, managed by Terraform instead of clicking through repo
# Settings. Kept SEPARATE from the root config on purpose: the main DO apply
# never needs a GitHub token, and this config never needs a DO one beyond
# the token *value* it stores as a secret.
#
# Manages (names must match .github/workflows/deploy-staging.yml — do not
# rename here without renaming there):
#   * repository environments `staging` and `production`
#   * environment secret DIGITALOCEAN_ACCESS_TOKEN (in each environment)
#   * repository variable DO_DEPLOY_ENABLED (the workflow's master gate)
#
# Auth: a GitHub token with repo admin scope via the GITHUB_TOKEN env var.
# The DO token comes in as TF_VAR_do_token — pass it via env, never write it
# into a *.tfvars file that could be committed.
#
# STATE CAVEAT (honest): github_actions_environment_secret stores the
# PLAINTEXT secret value in this config's Terraform state. State here is
# local (no backend block): run this from a trusted machine, keep
# terraform.tfstate off git (.gitignore must cover *.tfstate), or point a
# backend at the private state bucket from infra/bootstrap if you prefer —
# either way, treat the state file as containing the DO token.
#
# This config is optional: the three settings can equally be clicked into
# repo Settings by hand; Terraform-managing them is Marc's stated preference.
#
# `terraform validate` has NOT been run here (Terraform not installed in the
# authoring environment); parses with python-hcl2 only.

terraform {
  required_version = ">= 1.7"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
  # No backend block: local state, deliberately (see caveat above).
}

provider "github" {
  owner = var.github_owner
  # token via GITHUB_TOKEN env var
}

variable "github_owner" {
  type    = string
  default = "msd2"
}

variable "repository" {
  type    = string
  default = "auto-insight"
}

variable "do_token" {
  description = "DigitalOcean API token stored as DIGITALOCEAN_ACCESS_TOKEN in each repository environment. Pass via TF_VAR_do_token env var only."
  type        = string
  sensitive   = true
}

variable "deploy_enabled" {
  description = "Value of the DO_DEPLOY_ENABLED repository variable — the deploy workflow's master gate. Applying this config is the deliberate arming act, hence default true; set false to disarm without deleting anything."
  type        = bool
  default     = true
}

variable "environments" {
  type    = list(string)
  default = ["staging", "production"]
}

resource "github_repository_environment" "env" {
  for_each    = toset(var.environments)
  repository  = var.repository
  environment = each.key

  # TODO(later): protection rules — e.g. required reviewers on production
  # once a deploy-production workflow exists:
  # reviewers { users = [<id>] }
  # deployment_branch_policy { protected_branches = true, custom_branch_policies = false }
}

resource "github_actions_environment_secret" "do_token" {
  for_each        = github_repository_environment.env
  repository      = var.repository
  environment     = each.value.environment
  secret_name     = "DIGITALOCEAN_ACCESS_TOKEN" # matches deploy-staging.yml
  plaintext_value = var.do_token
}

resource "github_actions_variable" "do_deploy_enabled" {
  repository    = var.repository
  variable_name = "DO_DEPLOY_ENABLED" # matches deploy-staging.yml's gate
  value         = var.deploy_enabled ? "true" : "false"
}
