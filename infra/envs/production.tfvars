# production — NOT USED YET (staging-only pilot until the promote step in
# README.md §Promote is exercised). Separate state key:
#   terraform init -backend-config="key=production/terraform.tfstate"
#   terraform apply -var-file=envs/production.tfvars

environment = "production"
region      = "lon1" # TODO: Marc to confirm
app_region  = "lon"

# Production is NEVER deployed automatically: it tracks a `production`
# branch that only moves when a staging-verified sha is promoted (fast-
# forwarded) to it — see README.md §Promote. deploy_on_push=true is safe
# because pushing that branch IS the deliberate promote action; set false
# for a doctl-triggered flow instead if pushing feels too easy.
github_branch  = "production"
deploy_on_push = true

db_size               = "db-s-1vcpu-1gb" # revisit sizing before go-live
api_instance_count    = 1
worker_instance_count = 1

# DNS — off until the domain exists. Then:
#   domain        = "<the domain>"
#   manage_dns    = true
#   app_subdomain = "app"   # app.<domain>; zone stays owned by staging
manage_dns         = false
create_domain_zone = false # NEVER true here — staging owns the zone resource
app_subdomain      = "app"
