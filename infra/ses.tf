# SES — PLACEHOLDER ONLY. Email sending is Phase 3 (docs/03-roadmap.md);
# nothing is provisioned in Phase 0. Kept as a commented skeleton so the
# eventual shape is agreed now:
#
#   * one domain identity per sending domain (org sender identities per
#     docs/02-architecture.md — pilot likely subdomains of one platform
#     domain, e.g. <org>.mail.<product-domain>),
#   * a configuration set with event publishing → SNS → HTTPS webhook on the
#     api (delivery/bounce/complaint → email_events + suppressions),
#   * SES starts in SANDBOX against staging with verified test addresses;
#     production access is requested during Phase 3 with a warm-up plan.
#
# resource "aws_ses_domain_identity" "platform" {
#   domain = var.sender_domain            # TODO(phase-3): add variable
# }
#
# resource "aws_ses_domain_dkim" "platform" {
#   domain = aws_ses_domain_identity.platform.domain
# }
#
# resource "aws_ses_configuration_set" "main" {
#   name = "${var.project}-${var.environment}"
# }
#
# resource "aws_sns_topic" "ses_events" {
#   name = "${var.project}-${var.environment}-ses-events"
# }
#
# resource "aws_ses_event_destination" "sns" {
#   name                   = "sns"
#   configuration_set_name = aws_ses_configuration_set.main.name
#   enabled                = true
#   matching_types         = ["send", "delivery", "bounce", "complaint"]
#   sns_destination {
#     topic_arn = aws_sns_topic.ses_events.arn
#   }
# }
#
# resource "aws_sns_topic_subscription" "webhook" {
#   topic_arn = aws_sns_topic.ses_events.arn
#   protocol  = "https"
#   endpoint  = "https://<staging-domain>/webhooks/ses"   # TODO(phase-3)
# }
