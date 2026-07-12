# infra/ — DigitalOcean infrastructure (Terraform)

Status: **WP 0.4 authoring only.** No DigitalOcean account exists; nothing
here has ever been applied, and `terraform validate` has **not** been run on
any of the three configs (Terraform is not installed in the authoring
environment — every `.tf`/`.tfvars` file parses with python-hcl2, but run
`terraform init && terraform validate` in each config as the first act once
an account exists and expect to fix nits). The GitHub workflow
(`.github/workflows/deploy-staging.yml`) is gated off until the token exists
— see its header comment for exactly how the gate works.

> History: this directory originally held an AWS skeleton (ECS Fargate + RDS
> + SES). Marc redirected hosting to DigitalOcean and email to Postmark on
> 2026-07-12; the AWS files were replaced wholesale. The decision record
> below covers both the AWS routes we abandoned and the DO alternatives.
> A follow-up direction: **manage everything Terraform *can* manage in
> Terraform** — hence the bootstrap and github mini-configs.

## Layout — three configs, applied in order

| Order | Config | State | Purpose |
|---|---|---|---|
| 1 | `bootstrap/` | **local** (one-shot) | Spaces access key + state bucket the root backend needs — the chicken-and-egg config; its outputs feed the root backend (see its header) |
| 2 | `.` (root) | Spaces backend, one key per environment | everything DO per environment: app, database, firewall, project, DNS |
| 3 | `github/` | **local**, optional | GitHub repo environments, `DIGITALOCEAN_ACCESS_TOKEN` secret, `DO_DEPLOY_ENABLED` gate variable — separate so the DO apply never needs a GitHub token |

Root-config files, per concern:

| File | Concern |
|---|---|
| `versions.tf` | terraform/provider pins; Spaces (s3-compatible) state backend, commented until bootstrap has run |
| `providers.tf` | DO provider — token via `DIGITALOCEAN_TOKEN` env var, never in files |
| `variables.tf` | all knobs, pilot-sized defaults; region `lon1`/`lon` assumed, Marc to confirm |
| `project.tf` | DO project grouping the app + DB per environment (no flat resource soup) |
| `database.tf` | Managed Postgres 16 (smallest tier), app db + user, app-only firewall, composed `DATABASE_URL` |
| `app.tf` | the App Platform app: api service, Procrastinate **worker**, `PRE_DEPLOY` migrate job, web static site, `/api` ingress, deployment-failure alert, custom-domain block (gated) |
| `dns.tf` | `digitalocean_domain` + CNAME record, gated by `manage_dns` (default **false**) so applies work before a domain exists; assumes registrar NS delegation to DO |
| `docker/api.Dockerfile` | one uv-based image for api/worker/migrate (repo-root build context) |
| `outputs.tf` | app id/URL/fqdn for doctl + bootstrap checks |
| `envs/*.tfvars` | per-environment knobs (staging tracks `main` and owns the DNS zone; production tracks `production` branch, `app.` subdomain) |
| `.gitignore` | keeps all three configs' state files (which contain secrets) out of git |

## What still cannot be Terraform-managed, and why

- **DO account creation + billing** — no API exists before you have an account.
- **DO API token creation** — the credential Terraform itself authenticates
  with; can't be created by the thing that needs it (DO console, once).
- **DO GitHub-app OAuth** (lets App Platform build from the repo) — an OAuth
  browser flow with **no API**; explicitly a one-time console act.
- **Registrar-side NS delegation** of the domain to DO's nameservers — happens
  at the registrar, outside DO's API. After it, all records are Terraform
  (`dns.tf`).
- **Postmark** — no first-party Terraform provider worth depending on, and
  Phase 3 needs exactly one account, per-sender-domain DKIM/return-path DNS
  records, and a server token that lands as an App Platform SECRET env var
  (`POSTMARK_SERVER_TOKEN`, placeholder noted in `app.tf`). Console + DNS
  runbook territory — tracked in the roadmap's Phase 3 non-code row. (The
  DNS records themselves CAN go in `dns.tf` once the sender domains are DO-
  hosted.)

Everything else — including the GitHub repo settings the deploy workflow
reads — is in one of the three configs.

## Runtime decision

**DECIDED: DigitalOcean App Platform (+ DO Managed Postgres 16).**

The shape of the problem: one HTTP api, one **long-running non-HTTP
Procrastinate worker**, a static SPA, migrations on deploy, one small
Postgres. The worker is what kills most "simple" platforms — it serves no
requests, so anything that only hosts request-serving apps (AWS App Runner
throttles CPU outside request handling; same story for most PaaS web tiers)
either starves it or forces a second runtime.

**App Platform fits exactly** because it has a first-class **worker
component**: same build, same env, no port, no health-check contortions, CPU
never throttled. One app spec gives us all four components (api service,
worker, `PRE_DEPLOY` migration job, static site) plus native GitHub CD, TLS,
and a CDN for the SPA — things the AWS design needed an ALB, ACM, ECR, OIDC
roles, one-off `run-task` wiring and ~15 Terraform resources to approximate.

Rejected alternatives:

- **AWS ECS Fargate** (the previous recommendation, and the best AWS
  option): workable, and the earlier analysis stands *within AWS* — but it
  carries VPC/ALB/IAM/ECR/OIDC plumbing that is pure overhead at pilot
  scale. With SES gone (→ Postmark), the "email already pulls us to AWS"
  rationale is dead, and nothing else does.
- **AWS App Runner**: rejected earlier for the worker-CPU-throttling reason
  above; DO's worker component is precisely the thing it lacked.
- **DOKS (managed Kubernetes)**: strictly more moving parts (cluster
  upgrades, ingress controller, manifests/Helm, registry) for zero pilot
  benefit.
- **Droplets**: cheapest raw compute but hand-rolled deploys, TLS, process
  supervision, patching — undifferentiated server admin the pilot shouldn't
  fund.

**Build decisions** (also in `app.tf`'s header): App Platform builds
**straight from the GitHub repo** via its native integration — no DOCR, no
CI-built images; `deploy_on_push` on `main` *is* the staging CD mechanism,
and there's one less registry and token to manage. Build method is a
**Dockerfile** (`docker/api.Dockerfile`), not buildpacks, because the api is
uv-managed (uv.lock, no requirements.txt) and DO's Python buildpack doesn't
speak uv; the web static site does use the Node buildpack, which fits npm
exactly.

**Estimated pilot cost**: api + worker at basic-xxs ($5/mo each) + managed
PG db-s-1vcpu-1gb ($15/mo) + static site (free tier) + Spaces for state
($5/mo flat) ≈ **$30–40/mo**, plus Postmark ~$15/mo (10k emails).
Comparable AWS build-out was ~$60–65/mo with far more to operate.

## Deploy flow (once armed)

1. Merge to `main` → **App Platform itself** detects the push (GitHub
   integration, `deploy_on_push=true`), rebuilds all components, runs the
   `migrate` PRE_DEPLOY job (`alembic upgrade head` — a failed migration
   aborts the rollout), and rolls the app. There is no CI-side deploy step.
2. `.github/workflows/deploy-staging.yml` is therefore an **observer, not a
   deployer**: gated on `DO_DEPLOY_ENABLED`, it uses doctl to wait for the
   deployment DO triggered for this push and fails the check if that
   deployment fails — so a red deploy is visible on the commit in GitHub,
   not just in the DO console. `workflow_dispatch` can also force a
   redeploy (`doctl apps create-deployment`).
3. Infra changes (this directory) are applied **manually** (`terraform apply
   -var-file=envs/staging.tfvars`) for the pilot; nothing in CI holds a
   write-scope token beyond the observer's read/redeploy needs.

## Promote to production (manual, deliberate)

Production is a **second App Platform app + database cluster** (same module,
`envs/production.tfvars`, separate state key) tracking a `production`
branch. Nothing reaches it automatically. To promote:

1. Verify staging is green at the sha you want (staging app + this repo's CI).
2. Fast-forward the `production` branch to that sha and push:
   `git push origin <sha>:production`. That push is the deliberate promote
   action — App Platform rebuilds production from it, runs migrations
   (PRE_DEPLOY job), and rolls out. (If a branch push feels too easy a
   trigger, set `deploy_on_push=false` in production.tfvars and use
   `doctl apps create-deployment <prod-app-id>` instead.)
3. First-ever production apply must revisit sizing in `production.tfvars`.
   Databases are per-environment clusters — production data never derives
   from staging. (DO's cluster **fork** exists for cloning production into a
   debugging environment, not for promotes.)
4. Smoke-check `/health` on the production URL and record the promoted sha
   in `docs/STATUS.md`.

## Unblocking actual deployment — what Marc must provide

Console/manual items are limited to the "cannot be Terraform-managed" list
above; everything else lands as tfvars or env vars to one of the three
configs.

| # | Needed | Where it goes |
|---|---|---|
| 1 | **DigitalOcean account** (team created, billing set up) | console — unavoidable (see list above) |
| 2 | **API token** (write scope) | operator env vars only: `DIGITALOCEAN_TOKEN` for the DO applies, `TF_VAR_do_token` for the `github/` apply (which stores it as the `DIGITALOCEAN_ACCESS_TOKEN` environment secret — no repo-Settings clicking) |
| 3 | **GitHub personal access token** (repo admin on `msd2/auto-insight`) | operator env var `GITHUB_TOKEN`, only when applying `github/` |
| 4 | **DO GitHub app authorisation** for `msd2/auto-insight` (one-time OAuth, no API — see list above) | DO console → App Platform |
| 5 | **Region confirmation** (`lon1`/`lon` assumed; state bucket `ams3` — Spaces has no lon1) | `envs/*.tfvars`, `bootstrap/` variables, `versions.tf` backend endpoint |
| 6 | **Domain** + registrar NS delegation to DO | then `domain`/`manage_dns`/`create_domain_zone` in `envs/*.tfvars` (`dns.tf` does the rest) |
| 7 | **Postmark account** + sender-domain DKIM/return-path DNS verification (Phase 3, but account approval has lead time — start early) | Postmark console; server token → App Platform SECRET env `POSTMARK_SERVER_TOKEN` |

The `DO_DEPLOY_ENABLED=true` master switch is no longer a hand-created
variable: applying `github/` sets it (default `true`; `-var deploy_enabled=false`
to disarm).

## Bootstrap (first-ever apply, in order)

Console steps in the whole sequence: **account/billing (a), token creation
(a), the DO GitHub-app OAuth (e)** — everything else is Terraform.

a. Create the DO account + billing; create an API token (console, once).
   Export `DIGITALOCEAN_TOKEN=…`.
b. **`bootstrap/`**: two-phase apply exactly as its header documents —
   `terraform init`, `apply -target=digitalocean_spaces_key.terraform_state`,
   export the key outputs as `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
   (s3-backend quirk: AWS names, Spaces credentials), `apply` again for the
   bucket. Local state, kept on the operator machine.
c. **Root config**: uncomment the backend in `versions.tf` (values = the
   bootstrap outputs), `terraform init`, `terraform validate`, then
   `terraform apply -var-file=envs/staging.tfvars`. Do the GitHub-app OAuth
   (step e) *before* this apply — App Platform validates repo access when
   the app is created.
d. Confirm the first deployment: migrate job ran, `/health` on the
   `app_live_url` output returns `database: "ok"`, worker component running.
e. **DO GitHub-app OAuth** (console, once — no API): authorise DO for
   `msd2/auto-insight`. Listed after (c) for narrative; in practice do it
   right after (a).
f. **`github/`**: `export GITHUB_TOKEN=… TF_VAR_do_token=…`, `terraform init
   && terraform apply`. This creates the `staging`/`production` repo
   environments, the `DIGITALOCEAN_ACCESS_TOKEN` secret, and flips
   `DO_DEPLOY_ENABLED` to `true` — the deploy-status workflow is now armed.
g. Push a trivial commit to `main`; watch DO auto-deploy and the observer
   workflow go green.

## Later hardening (tracked, deliberately skipped for the pilot)

- Scope the DO token more tightly (custom scopes are new-ish in DO; today it
  is effectively account-wide write — treat it accordingly).
- `preserve_path_prefix`/route-rewrite verification for `/api` and the
  `live_domain` CNAME value (TODOs in `app.tf`/`dns.tf`).
- Production DB: standby node (`node_count = 2`), connection pool sizing.
- Production GitHub environment protection rules (required reviewers) via
  `github/` once a deploy-production workflow exists (TODO in its main.tf).
- Consider a remote backend for `github/` state (contains the DO token) if
  more than one operator ever applies it.
- Postmark bounce/complaint webhook signing verification (Phase 3 WP 3.2).
