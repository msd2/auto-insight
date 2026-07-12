# staging — apply with:
#   terraform init            # backend key: staging/terraform.tfstate (versions.tf)
#   terraform apply -var-file=envs/staging.tfvars

environment = "staging"
region      = "lon1" # TODO: Marc to confirm region before first apply
app_region  = "lon"

# Staging CD is App Platform's own GitHub integration: push to main →
# rebuild → migrate (pre-deploy job) → rollout. See deploy-staging.yml.
github_branch  = "main"
deploy_on_push = true

# Pilot sizing — defaults in variables.tf already match; listed so the
# per-environment knobs are explicit.
db_size               = "db-s-1vcpu-1gb"
api_instance_count    = 1
worker_instance_count = 1

# DNS — off until Marc provides a domain and delegates its nameservers to
# DigitalOcean (registrar-side NS change; see dns.tf). Then:
#   domain             = "<the domain>"
#   manage_dns         = true
#   create_domain_zone = true   # staging owns the account-wide zone resource
manage_dns         = false
create_domain_zone = false
