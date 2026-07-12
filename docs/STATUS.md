# STATUS — Phase 0 execution

Last updated: 2026-07-12 (wave 2 landed — Phase 0 code work complete).
Read `CLAUDE.md` first if you haven't. This doc is the live state of Phase 0
(`docs/03-roadmap.md`) and must be updated whenever a work package lands.

## Where things stand

| WP | Task # | State |
|---|---|---|
| 0.1 Repo scaffold | #1 | **DONE** (PR #1, merged). Rebuilt from spec — the earlier background agent's work never landed. |
| 0.2 Schema & tenancy | #2 | **DONE**, commit `4adb02d`. 16-table baseline migration `d5d0e6b3dd72`; OrgContext repositories; tenancy + drift tests. |
| 0.3 Auth & membership | #3 | **DONE** — see "Wave 2 notes". Sessions/reset migration `cc8b261a61d9`; argon2; seed CLI; 33 api tests. |
| 0.4 Deploy pipeline authoring | #4 | **DONE (authoring)**, commit `e7248f5`. Execution blocked on Marc (AWS account etc. — see infra/README.md). |
| 0.5 Pack content | #5 | **DONE** — content `ecd4e8a` (wave 1) + preview wiring `582629a` (wave 2): /dev/packs renders all 4 packs from sample data. |

**Phase 0 exit criterion verified 2026-07-12** on a fresh database: alembic
upgrade head → `seed-org` CLI → api boot → `POST /auth/login` (session
cookie) → `GET /auth/me` returns user/org/role; unauthenticated → 401; and
`make lint` + `make test` green on the merged tree. What Phase 0 still needs
is *staging deployment*, which is the blocked WP 0.4 execution — everything
buildable without AWS is done.

Git: remote `origin` = github.com:msd2/auto-insight. Wave 2 was developed on
`claude/status-docs-review-jquyqc` (remote-session designated branch), one
checkpoint commit per verified WP (`wp<N.n>:` prefix): `e7248f5` (wp0.4),
`582629a` (wp0.5 preview), `4adb02d` (wp0.2), wp0.3 on top. Merge to `main`
via PR when ready; CI runs on `claude/**` pushes and PRs.

## Wave 2 notes

- **WP 0.2** — all 16 architecture-doc tables as typed SQLAlchemy 2 models
  (abstract `OrgOwned` supplies non-null indexed `org_id`); baseline
  migration `d5d0e6b3dd72` (autogen then hand-cleaned; downgrade verified;
  a test proves zero model↔schema drift). Repositories: frozen `OrgContext`,
  generic `OrgScopedRepository` (every query org-filtered, `add()` stamps
  org_id, cross-org update/delete return None/False), concrete repos with
  ownership checks on FK targets, unscoped `OrganisationRepository` for
  seeding; `repositories/deps.py` gives endpoints repositories, never
  sessions.
- **WP 0.3** — server-side sessions + single-use password-reset tokens
  (migration `cc8b261a61d9`; DB stores SHA-256 of opaque tokens). argon2id
  (argon2-cffi). Endpoints: /auth/login, /auth/logout, /auth/me,
  /auth/password-reset/{request,confirm}. Email unique per org; multi-org
  email logs in with `org_slug` (documented in `auth/__init__.py`).
  `EmailProvider` adapter interface + logging stub in
  `api/autoinsight/adapters/` (SES is Phase 3). Seed:
  `uv run python -m autoinsight.cli seed-org --name X --slug x --email e
  --user-name N --password p` (idempotent by slug).
- **WP 0.4** — CI `migrations` job (clean-DB alembic upgrade);
  `deploy-staging.yml` gated behind `AWS_DEPLOY_ENABLED` repo variable +
  `staging` GitHub environment (OIDC role, no stored keys); `infra/`
  Terraform skeleton. **Recommendation: ECS Fargate for api+worker** (App
  Runner can't host the non-HTTP Procrastinate worker). `terraform validate`
  not yet run (no terraform in the authoring env).
- **WP 0.5 preview** — `/dev/packs` + `/dev/packs/$slug` (outside AppShell)
  glob-import pack JSON from `content/` (no duplication); typed aggregate
  contract + data-driven Recharts components (seed of WP 2.1); per-pack
  Vitest smoke tests driven by the same glob.
- Toolchain note: remote container has no Docker daemon — Postgres 16 runs
  directly on port 5433 for tests (same credentials as compose). vitest
  pinned to v3 (v2 bundles vite 5). `procrastinate[psycopg]` extra warning:
  procrastinate 3.9 has no `psycopg` extra — tidy the spec in a future WP.

## WP 0.1 notes

Scaffold as specified in the roadmap: `api/` (FastAPI app factory,
pydantic-settings `config.py` with Procrastinate DSN derived from
DATABASE_URL, async SQLAlchemy `db.py`, `GET /health` always-200 with
`database: "ok"|"unavailable"`, `worker.py` wired to Procrastinate with no
jobs, empty `models/`/`repositories/`, async-template Alembic with
`target_metadata = None` and the URL injected from settings in `env.py`,
uv-managed pyproject, `/health` tests via httpx ASGITransport with the
`get_session` dependency overridden), `web/` (Vite + React 18.3 + TS,
TanStack Query + Router with code-based routes, recharts as dependency,
`/login` placeholder + AppShell layout route with Dashboard/Events/Surveys/
Reports sidebar and org-name placeholder, ESLint flat + Prettier +
Vitest/jsdom AppShell smoke test, `src/api/client.ts` fetch wrapper, dev
proxy `/api` → :8000), root (docker-compose postgres:16 on host 5433,
Makefile, .gitignore, .env.example, `.github/workflows/ci.yml` — api job
with postgres service, web job on Node 22).

Verified in the remote session: `make lint` (ruff + format + mypy strict,
eslint + tsc + prettier), `make test` (pytest ×2, vitest ×1),
`npm run build`, uvicorn boot → `/health` returns
`{"status":"ok","database":"unavailable"}` without a DB and
`{"status":"ok","database":"ok"}` against a real Postgres 16 on port 5433,
plus `alembic upgrade head` (no-op, connects cleanly). Caveat: the remote
container has no Docker daemon, so `docker-compose.yml` itself was not
booted — Postgres was run directly (same image version/port/credentials).
CI run 29168127548 on this branch is **green** (api job incl. postgres:16
service + pytest; web job incl. build), which covers the containerised path.

Version pins that mattered: vitest 3 (vitest 2 bundles vite 5, conflicts
with vite 6), uv pinned to Python 3.12 via `api/.python-version`.

## Next up

Phase 0 code work is complete. What remains before Phase 1 starts:

1. **WP 0.4 execution** (blocked on Marc, item 1 below): AWS account →
   bootstrap `terraform apply` → GitHub environment + `AWS_DEPLOY_ENABLED`
   → first staging deploy. Checklist in `infra/README.md` §"Unblocking
   actual deployment". The Phase 0 exit line ("logged-in user in a seeded
   org sees the app shell **on staging**") closes when this lands.
2. **Phase 1 wave planning**: WP 1.1 Spektrix adapter and 1.2 sync engine
   are the next buildable WPs (1.1 first — 1.2 depends on it); 1.3/1.4 UI
   can follow in parallel once the adapter's shape settles.
3. Small tidy: `procrastinate[psycopg]` extra no longer exists in
   procrastinate 3.9 — fix the pyproject spec alongside the first real job
   in WP 1.2.
4. `/login` is still a placeholder page — wire the real form to /auth/login
   when Phase 1 UI work opens `web/` again (was out of wave-2 scope).

## Blocked on Marc (only he can unblock)

1. **AWS account/credentials** → staging deploy (WP 0.4 execution). Full
   list of the six required items: `infra/README.md` §"Unblocking actual
   deployment" (account, region, bootstrap creds, `staging` environment
   with `AWS_ROLE_ARN`/`AWS_REGION`, `AWS_DEPLOY_ENABLED` variable, domain).
2. **Pack question sign-off** against real Culture Counts question banks
   (`content/` wording is DRAFT) — gates Phase 2 WPs 2.1/2.2.
3. Pilot org shortlist + product name (open questions in
   `docs/01-product-brief.md`).

## Environment notes

- Remote is github.com:msd2/auto-insight — check the Actions run after
  pushing; don't claim CI green without a green run. (No `gh` CLI in the
  remote container; use the GitHub MCP tools there.)
- Postgres via `docker-compose up -d db` on host port 5433 locally; in the
  remote container (no Docker daemon) run Postgres 16 directly on 5433.
