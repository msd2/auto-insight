# production — NOT USED YET (staging-only pilot until the promote step in
# README.md §Promote is exercised). Separate state key: change the backend
# `key` to production/terraform.tfstate via `terraform init -backend-config`.

environment = "production"
aws_region  = "eu-west-2" # TODO: confirm region with Marc

db_instance_class    = "db.t4g.small"
api_desired_count    = 1
worker_desired_count = 1

# ALWAYS a pinned, staging-verified image sha — never a moving tag.
# image_tag = "<git sha promoted from staging>"

# TODO(wp0.4-execution): production hardening not yet parameterised in the
# module: deletion_protection=true, skip_final_snapshot=false, longer backup
# retention. Add variables when production is actually provisioned.
