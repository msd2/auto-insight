# App Platform — one app per environment, four components from one repo:
#
#   service  api      FastAPI (HTTP, health-checked on /health)
#   worker   worker   Procrastinate consumer (long-running, no HTTP) — the
#                     component type that decided the platform (README
#                     §Runtime decision)
#   job      migrate  PRE_DEPLOY: `alembic upgrade head` runs before every
#                     deployment is promoted — migrations on every deploy,
#                     and a failed migration aborts the rollout
#   static   web      Vite build served from DO's CDN
#
# BUILD DECISION (recorded in README §Runtime decision):
#  * Source: App Platform builds STRAIGHT FROM THE GITHUB REPO via its native
#    integration (github{} blocks below). No DOCR, no CI-built images — with
#    deploy_on_push=true this IS the staging CD mechanism, and there is one
#    less registry + token to manage. DOCR only becomes worth it if we need
#    build artefacts CI has tested bit-for-bit.
#  * Method: Dockerfile (infra/docker/api.Dockerfile), not buildpacks — the
#    api is uv-managed (uv.lock, no requirements.txt) and DO's Python
#    buildpack doesn't speak uv. The web static site DOES use the Node
#    buildpack (npm is exactly what it expects).
#
# python-hcl2 parses this file but `terraform validate` has NOT run (not
# installed here) and no apply has ever happened — expect first-contact nits.

resource "digitalocean_app" "main" {
  spec {
    name   = "${var.project}-${var.environment}"
    region = var.app_region

    # App-wide env: injected into api, worker and the migrate job alike
    # (the static site ignores runtime env). SECRET-type values are
    # encrypted by DO after first apply and never shown again in the spec.
    env {
      key   = "DATABASE_URL"
      value = local.database_url
      type  = "SECRET"
      scope = "RUN_TIME"
    }

    # TODO(phase-3): POSTMARK_SERVER_TOKEN as a second SECRET env when the
    # Postmark EmailProvider lands (value set out-of-band, see README).

    service {
      name               = "api"
      instance_count     = var.api_instance_count
      instance_size_slug = var.api_instance_size
      http_port          = 8000

      github {
        repo           = var.github_repository
        branch         = var.github_branch
        deploy_on_push = var.deploy_on_push
      }

      source_dir      = "/" # build context = repo root (Dockerfile COPYs api/)
      dockerfile_path = "infra/docker/api.Dockerfile"

      run_command = "uvicorn autoinsight.main:app --host 0.0.0.0 --port 8000"

      health_check {
        http_path             = "/health"
        initial_delay_seconds = 10
        period_seconds        = 10
      }
    }

    worker {
      name               = "worker"
      instance_count     = var.worker_instance_count
      instance_size_slug = var.worker_instance_size

      github {
        repo           = var.github_repository
        branch         = var.github_branch
        deploy_on_push = var.deploy_on_push
      }

      source_dir      = "/"
      dockerfile_path = "infra/docker/api.Dockerfile"

      # Entrypoint per api/autoinsight/worker.py docstring.
      run_command = "procrastinate --app=autoinsight.worker.app worker"
    }

    job {
      name               = "migrate"
      kind               = "PRE_DEPLOY"
      instance_size_slug = var.api_instance_size

      github {
        repo           = var.github_repository
        branch         = var.github_branch
        deploy_on_push = var.deploy_on_push
      }

      source_dir      = "/"
      dockerfile_path = "infra/docker/api.Dockerfile"

      # Dockerfile WORKDIR is /app which contains api/'s contents, so
      # alembic.ini is found without -c.
      run_command = "alembic upgrade head"
    }

    static_site {
      name             = "web"
      environment_slug = "node-js"
      source_dir       = "web"
      build_command    = "npm ci && npm run build"
      output_dir       = "dist"

      github {
        repo           = var.github_repository
        branch         = var.github_branch
        deploy_on_push = var.deploy_on_push
      }
    }

    # Same-origin routing (no CORS): SPA at /, api under /api — mirroring the
    # Vite dev proxy (`/api` → :8000, no rewrite), so preserve_path_prefix
    # keeps the /api prefix on forwarded requests exactly like the dev proxy.
    # TODO(wp0.4-execution): confirm against web/src/api/client.ts + the api's
    # route prefixes on first deploy; flip preserve_path_prefix if the api
    # turns out to serve unprefixed routes.
    ingress {
      rule {
        component {
          name                 = "api"
          preserve_path_prefix = true
        }
        match {
          path {
            prefix = "/api"
          }
        }
      }

      rule {
        component {
          name = "web"
        }
        match {
          path {
            prefix = "/"
          }
        }
      }
    }

    # NOTE: no spec-level `database` attach block — DB access control is
    # managed explicitly via digitalocean_database_firewall (database.tf) and
    # the connection URL is composed in Terraform, so attaching would only
    # duplicate trust management.

    # TODO(wp0.4-execution): custom domain + alerts once Marc provides the
    # domain:
    # domain { name = "staging.<domain>" zone = "<domain>" type = "PRIMARY" }
    # alert { rule = "DEPLOYMENT_FAILED" }
  }
}
