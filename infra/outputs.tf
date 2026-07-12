output "app_id" {
  description = "App Platform app id — used by deploy-staging.yml (doctl) to watch deployments."
  value       = digitalocean_app.main.id
}

output "app_live_url" {
  description = "Default *.ondigitalocean.app URL until a custom domain is added."
  value       = digitalocean_app.main.live_url
}

output "app_fqdn" {
  description = "Custom hostname (empty until manage_dns=true)."
  value       = local.app_fqdn
}

output "db_cluster_id" {
  value = digitalocean_database_cluster.main.id
}

output "db_private_host" {
  description = "Private-network Postgres host (the composed DATABASE_URL uses this)."
  value       = digitalocean_database_cluster.main.private_host
}
