# DO Managed Postgres 16 — smallest tier for the pilot. One cluster per
# environment; app data + Procrastinate job queue in the same database
# (per docs/02-architecture.md).

resource "digitalocean_database_cluster" "main" {
  name       = "${var.project}-${var.environment}-pg"
  engine     = "pg"
  version    = "16"
  size       = var.db_size
  region     = var.region
  node_count = var.db_node_count

  # Managed PG includes daily backups + PITR on all tiers — no knobs needed
  # at pilot size. For production consider node_count = 2 (standby) later.
}

# Dedicated application database (the cluster's built-in `defaultdb` stays
# unused) and a dedicated app user, so credentials can be rotated without
# touching doadmin.
resource "digitalocean_database_db" "app" {
  cluster_id = digitalocean_database_cluster.main.id
  name       = var.db_name
}

resource "digitalocean_database_user" "app" {
  cluster_id = digitalocean_database_cluster.main.id
  name       = "${var.project}_app"
}

# Trusted sources: only the App Platform app may reach the cluster. This
# replaces all public access (DO managed DBs are otherwise reachable from
# anywhere with credentials).
resource "digitalocean_database_firewall" "main" {
  cluster_id = digitalocean_database_cluster.main.id

  rule {
    type  = "app"
    value = digitalocean_app.main.id
  }

  # TODO(wp0.4-execution): add a temporary `ip_addr` rule for the operator's
  # IP when running one-off psql/bootstrap tasks, then remove it.
}

locals {
  # SQLAlchemy-async URL for the app user. Notes:
  #  * private_host keeps traffic inside the DO network (app + DB same region).
  #  * DO managed PG requires TLS; SQLAlchemy's asyncpg dialect accepts
  #    `?ssl=require` (asyncpg itself does not understand libpq's `sslmode`).
  #    TODO(wp0.4-execution): verify on first boot; if the driver complains,
  #    fall back to handling ssl in api config rather than the URL.
  #  * The user password transits Terraform state — acceptable for the pilot
  #    given the state backend is a private Spaces bucket; revisit if state
  #    handling changes. (Alternative considered: App Platform bindable
  #    ${db.DATABASE_URL} variables avoid state exposure but emit a
  #    postgres:// scheme URL and the doadmin user, so we compose our own.)
  database_url = "postgresql+asyncpg://${digitalocean_database_user.app.name}:${digitalocean_database_user.app.password}@${digitalocean_database_cluster.main.private_host}:${digitalocean_database_cluster.main.port}/${var.db_name}?ssl=require"
}
