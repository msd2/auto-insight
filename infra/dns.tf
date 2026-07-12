# DNS — guarded so applies work while Marc has no domain yet:
#   manage_dns = false (default)  →  zero DNS resources, no app domain block.
#
# Model once a domain exists: the domain's NAMESERVERS ARE DELEGATED TO
# DIGITALOCEAN (ns1/ns2/ns3.digitalocean.com) at the registrar — that
# registrar-side NS change is the one manual DNS act; every record after it
# is Terraform here. digitalocean_domain creates the zone (in exactly ONE
# environment: create_domain_zone=true in staging.tfvars only, so the two
# environments don't fight over the same zone resource); each environment
# then manages its own CNAME.
#
# The app spec's matching domain block lives in app.tf (dynamic "domain",
# same manage_dns guard) WITHOUT its `zone` attribute — zone would make App
# Platform manage the DNS record itself, colliding with the explicit record
# below. App Platform still provisions the TLS certificate either way.

locals {
  # staging.<domain> by default; production overrides via app_subdomain="app".
  app_subdomain = var.app_subdomain != "" ? var.app_subdomain : var.environment
  app_fqdn      = var.manage_dns ? "${local.app_subdomain}.${var.domain}" : ""
}

resource "digitalocean_domain" "main" {
  count = var.manage_dns && var.create_domain_zone ? 1 : 0
  name  = var.domain
}

resource "digitalocean_record" "app" {
  count = var.manage_dns ? 1 : 0

  # digitalocean_domain's id is the domain name; referencing it (when this
  # environment owns the zone) orders creation, otherwise use the name.
  domain = var.create_domain_zone ? digitalocean_domain.main[0].id : var.domain
  type   = "CNAME"
  name   = local.app_subdomain
  # CNAME targets need the trailing dot. live_domain is the app's default
  # *.ondigitalocean.app hostname.
  # TODO(wp0.4-execution): confirm live_domain is populated on first apply
  # (it is set once the app has deployed once); fall back to
  # replace(digitalocean_app.main.default_ingress, "https://", "") if not.
  value = "${digitalocean_app.main.live_domain}."
  ttl   = 300
}
