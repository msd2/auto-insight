# DO project: groups this environment's resources in the control panel so
# the account isn't a flat resource soup. One project per environment.

resource "digitalocean_project" "main" {
  name        = "${var.project}-${var.environment}"
  description = "Auto Insight ${var.environment} — automated audience insight for arts organisations"
  purpose     = "Web Application"
  environment = var.environment == "production" ? "Production" : "Staging"

  resources = [
    digitalocean_app.main.urn,
    digitalocean_database_cluster.main.urn,
  ]
  # Note: domains have URNs too, but digitalocean_domain is created in at
  # most ONE environment (create_domain_zone, dns.tf) while this project
  # exists per environment — assigning it here would tug the domain between
  # projects. Leave the domain in the account default project.
}
