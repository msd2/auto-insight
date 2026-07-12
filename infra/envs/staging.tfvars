# staging — apply with:
#   terraform init            # backend key: staging/terraform.tfstate (versions.tf)
#   terraform apply -var-file=envs/staging.tfvars

environment = "staging"
aws_region  = "eu-west-2" # TODO: confirm region with Marc before first apply

# Pilot sizing — defaults in variables.tf already match; listed here so the
# knobs per environment are explicit.
db_instance_class    = "db.t4g.micro"
api_desired_count    = 1
worker_desired_count = 1
image_tag            = "staging"
