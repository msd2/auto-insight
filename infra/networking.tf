# Networking — DEFAULT VPC for the pilot (deliberate).
#
# Decision: use the account's default VPC and its public subnets rather than
# building a custom VPC + NAT gateways. Rationale for a pilot:
#   * NAT gateways are the single biggest fixed cost a small VPC adds
#     (~$35/mo each before traffic) and buy nothing we need yet.
#   * Fargate tasks in public subnets with assign_public_ip=true can reach
#     ECR/Spektrix/Culture Counts/Claude directly; inbound is still closed by
#     security groups (the app SG has no ingress until the ALB lands).
#   * RDS stays publicly_accessible=false regardless.
# Revisit (private subnets + NAT or VPC endpoints) before production handles
# real PII at scale — tracked in README.md §Later hardening.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Shared security group for the api + worker Fargate tasks.
resource "aws_security_group" "app" {
  name_prefix = "${var.project}-${var.environment}-app-"
  description = "Auto Insight api + worker tasks"
  vpc_id      = data.aws_vpc.default.id

  # No ingress yet: the worker needs none, and the api will receive traffic
  # only from the ALB security group once the ALB is added.
  # TODO(wp0.4-execution): when adding the ALB, add
  #   ingress { from_port = 8000, to_port = 8000, protocol = "tcp",
  #             security_groups = [aws_security_group.alb.id] }

  egress {
    description = "All outbound (ECR pulls, Postgres, Spektrix/CC/Claude APIs)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# TODO(wp0.4-execution): ALB for the api service — skeleton intentionally
# commented until the account/domain exist (needs an ACM certificate).
#
# resource "aws_security_group" "alb" { ... 443 from 0.0.0.0/0 ... }
# resource "aws_lb" "api" { ... }
# resource "aws_lb_target_group" "api" { port = 8000, target_type = "ip",
#   health_check { path = "/health" } }
# resource "aws_lb_listener" "https" { ... certificate_arn = ACM cert ... }
