# infra/ — AWS infrastructure (Terraform)

Status: **WP 0.4 authoring only.** No AWS account exists; nothing here has
ever been applied, and `terraform validate` has **not** been run (Terraform is
not installed in the authoring environment — run `terraform init &&
terraform validate` as the first act once an account exists, and expect to
fix nits). The GitHub Actions deploy workflow
(`.github/workflows/deploy-staging.yml`) is gated off until secrets exist —
see its header comment for exactly how the gate works.

Layout: a single root module, parameterised by `environment`, with one state
file and one tfvars per environment (`envs/staging.tfvars`,
`envs/production.tfvars`). Files are per concern:

| File | Concern |
|---|---|
| `versions.tf` | terraform/provider pins; S3 state backend (commented until account exists) |
| `providers.tf` | AWS provider + default tags |
| `variables.tf` | all knobs, pilot-sized defaults |
| `networking.tf` | **default VPC decision** + app security group; ALB commented TODO |
| `rds.tf` | Postgres 16 (RDS-managed master password → Secrets Manager) |
| `ecr.tf` | one image repo (api + worker share the image) + lifecycle policy |
| `runtime.tf` | ECS Fargate cluster, api + worker task definitions and services |
| `iam.tf` | ECS execution/task roles; GitHub OIDC provider + deploy role |
| `secrets.tf` | Secrets Manager containers (values set out-of-band); SSM convention |
| `ses.tf` | Phase 3 placeholder, fully commented |
| `outputs.tf` | values CI and bootstrap need |

## Runtime decision: App Runner vs ECS Fargate

**RECOMMENDATION: ECS Fargate for both api and worker.**

The deciding fact is the worker. It is a long-running Procrastinate consumer
(`procrastinate --app=autoinsight.worker.app worker`) that polls Postgres —
it serves no HTTP. App Runner only hosts request-serving applications: it
requires a port that answers health checks, scales on request concurrency,
and (critically) **throttles container CPU when no requests are in flight**,
which would silently starve a background worker precisely when it has no
traffic — i.e. always. The workarounds (bolt a dummy HTTP server onto the
worker and ping it to keep CPU allocated, or run api on App Runner and the
worker somewhere else) either fight the platform or leave us operating two
runtimes anyway. Since we must run ECS (or similar) for the worker
regardless, the *simplest* system is one Fargate cluster running two
services from one image — one deploy pipeline, one IAM/networking/logging
story, and the same `run-task` mechanism gives us one-off migration tasks
for free. App Runner's genuine advantages (built-in HTTPS endpoint, faster
first deploy) only ever applied to the api half, and are offset by needing
an ALB + ACM cert once anyway for a custom domain. Fargate at pilot size
(2 × 0.25 vCPU/512 MiB, ~$25–30/mo + ALB ~$20/mo + RDS t4g.micro ~$15/mo)
is well within pilot budget.

Also considered and rejected for the pilot: EC2 (undifferentiated server
admin), Lambda (the worker is a persistent poller; FastAPI-on-Lambda adds
cold-start and packaging friction), Elastic Beanstalk (legacy posture).

## Deploy flow (once armed)

1. Merge to `main` → `deploy-staging.yml` runs: build image → push
   `:sha` + `:staging` to ECR → one-off Fargate task runs
   `alembic upgrade head` → `ecs update-service --force-new-deployment` for
   api + worker.
2. Infra changes (this directory) are applied **manually** (`terraform apply
   -var-file=envs/staging.tfvars`) for the pilot; CI deploys application code
   only. Revisit if infra churn becomes frequent.
3. Web SPA hosting is TODO(wp0.4-execution): S3+CloudFront vs serving the
   built SPA from the api container. Decide when the domain exists.

## Promote to production (manual, deliberate)

Production is never deployed automatically. To promote:

1. Pick the staging-verified image: the `:<git sha>` tag currently running on
   staging (`aws ecs describe-services` → task definition → image).
2. Provision/refresh production infra:
   `terraform init -backend-config="key=production/terraform.tfstate" &&
   terraform apply -var-file=envs/production.tfvars -var image_tag=<sha>`
   (first production apply must also revisit the hardening TODOs flagged in
   `envs/production.tfvars` and `rds.tf`).
3. Run migrations against production via the same one-off task pattern.
4. `aws ecs update-service --force-new-deployment` for both services (or let
   the task-definition change from step 2 roll them).
5. Smoke-check `/health` and record the promoted sha in `docs/STATUS.md`.

A `deploy-production.yml` with a `workflow_dispatch` sha input + required
reviewers on a `production` GitHub environment is the intended end state;
authoring it is deferred until staging has actually deployed once.

## Unblocking actual deployment — what Marc must provide

| # | Needed | Where it goes |
|---|---|---|
| 1 | **AWS account** (fresh account recommended; billing set up) | — |
| 2 | **Region decision** (files assume `eu-west-2` London) | `variables.tf` / `envs/*.tfvars`, backend block in `versions.tf`, GitHub env variable `AWS_REGION` |
| 3 | **Bootstrap credentials** — one human/root-adjacent IAM user or SSO role able to run the first `terraform apply` (which then creates the CI OIDC role; CI never needs long-lived keys) | operator's local `aws configure` / SSO, never the repo |
| 4 | **GitHub environment `staging`** with secret `AWS_ROLE_ARN` = `terraform output github_deploy_role_arn`, variable `AWS_REGION` | repo Settings → Environments |
| 5 | **Repository variable `AWS_DEPLOY_ENABLED` = `true`** — the master switch; the deploy workflow is a guaranteed no-op until this exists | repo Settings → Secrets and variables → Actions → Variables |
| 6 | **Domain** for staging (and later production) — needed for ALB + ACM cert, and eventually SES sender identities (Phase 3) | `networking.tf` ALB TODO; `ses.tf` |

## Bootstrap (first-ever apply, run manually)

1. Create the state bucket + DynamoDB lock table; uncomment the backend block
   in `versions.tf`; `terraform init`.
2. `terraform apply -var-file=envs/staging.tfvars` (expect to iterate — this
   config has never met a real AWS API; run `terraform validate` first).
3. Compose `DATABASE_URL` from `terraform output db_endpoint` + the RDS
   master secret (`db_master_user_secret_arn`) and store it:
   `aws secretsmanager put-secret-value --secret-id autoinsight/staging/database-url --secret-string 'postgresql+asyncpg://…'`.
4. Do items 4–5 from the table above, push to `main`, watch the deploy run.

## Later hardening (tracked, deliberately skipped for the pilot)

- Private subnets + NAT (or VPC endpoints) instead of default-VPC public
  subnets with public IPs (see `networking.tf` header for the rationale).
- Tighten the OIDC trust to the exact `environment:staging` subject and the
  ECS deploy policy with `ecs:cluster` conditions (`iam.tf` TODOs).
- Immutable ECR tags + task definitions pinned to shas in CI
  (`deploy-staging.yml` TODO).
- Container Insights, alarms, RDS Performance Insights.
