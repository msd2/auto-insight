# STATUS — Phase 0 execution

Last updated: 2026-07-11 (WP 0.1 landed).
Read `CLAUDE.md` first if you haven't. This doc is the live state of Phase 0
(`docs/03-roadmap.md`) and must be updated whenever a work package lands.

## Where things stand

| WP | Task # | State |
|---|---|---|
| 0.1 Repo scaffold | #1 | **DONE** — see "WP 0.1 notes" below. The prior background agent's work never landed; rebuilt from spec. |
| 0.2 Schema & tenancy | #2 | Not started (wave 2) |
| 0.3 Auth & membership | #3 | Not started (wave 2) |
| 0.4 Deploy pipeline authoring | #4 | Not started (wave 2). AWS *deployment* is blocked on account/credentials — authoring only for now. |
| 0.5 Pack content | #5 | **DONE**, committed `ecd4e8a`. Preview UI wiring remains (wave 2, agent C). |

Git: remote `origin` = github.com:msd2/auto-insight. Wave-1 commits on
`main`: `c79266c` (planning docs), `ecd4e8a` (wp0.5 content), `41256fe` +
`a7cce01` (handoff docs). WP 0.1 was developed on branch
`claude/status-docs-review-jquyqc` (remote-session designated branch) — merge
to `main` before starting wave 2. Convention: one checkpoint commit per
verified WP, message prefix `wp<N.n>:`.

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
First CI run on push should confirm the compose-equivalent api job.

Version pins that mattered: vitest 3 (vitest 2 bundles vite 5, conflicts
with vite 6), uv pinned to Python 3.12 via `api/.python-version`.

## Wave 2 (after wp0.1 commit) — three parallel agents, disjoint paths

Approved plan (full text: `/Users/marc.dunford/.claude/plans/giggly-tickling-kahan.md`):

- **Agent A — `api/` only, WP 0.2 then 0.3 sequentially.** 0.2: SQLAlchemy
  models + first Alembic migration for the entire data model in
  `docs/02-architecture.md` §Data model; `OrgContext`-scoped repository
  layer; tests (against compose Postgres) proving cross-org access is
  impossible through the layer. 0.3: email+password auth (argon2/bcrypt),
  secure session cookies, password reset with email send stubbed behind the
  `EmailProvider` interface, member/admin roles, login/logout/me endpoints,
  CLI seed command (`python -m autoinsight.cli seed-org`), auth tests. No
  self-serve signup.
- **Agent B — `.github/` + `infra/` only, WP 0.4 authoring.** CI
  migration-check job; gated deploy-to-staging workflow (no-op without AWS
  secrets); Terraform skeleton; infra/README.md records the App Runner vs ECS
  recommendation and the manual promote step.
- **Agent C — `web/src` + at most one new api route, WP 0.5 preview wiring.**
  Dev catalogue preview route rendering each pack in `content/packs/*/v1.json`
  from its `sample_dataset` (Recharts) + `example_narrative`; Vitest smoke
  test per pack. Read `content/README.md` first — the aggregate shapes there
  are the canonical chart-data contract (also used by Phase 5 real
  aggregation). Key format notes: distribution aggregates are
  `{labels, counts}` mapping straight to Recharts; NPS has `counts_by_score`
  + precomputed `score`; free text has `{answered, snippets[]}`; cuts are
  `cuts.<key>.segments[]`; multi_choice percentages use `answered` as
  denominator, not sum of counts; `example_themes`/`example_narrative` are
  preview-only.

Then integration verification (coordinator, not agents): `make lint && make
test` on merged tree; compose db → `alembic upgrade head` → seed CLI → boot
api → curl login/me with session cookie → web build with preview route. That
end-to-end path is the Phase 0 exit criterion ("logged-in user in a seeded
org sees the app shell"). Checkpoint commit per WP; update tasks #1–#4.

## Blocked on Marc (only he can unblock)

1. **AWS account/credentials + hosting decision** → actual staging deploy
   (WP 0.4 execution). A new blocked task should be created when 0.4
   authoring completes.
2. **Pack question sign-off** against real Culture Counts question banks
   (`content/` wording is DRAFT) — gates Phase 2 WPs 2.1/2.2.
3. Pilot org shortlist + product name (open questions in
   `docs/01-product-brief.md`).

## Environment notes

- Session task list (#1–#5) mirrors this table; keep both in sync.
- Remote is github.com:msd2/auto-insight — once the CI workflow lands, check
  the Actions run after pushing (`gh run watch`); don't claim CI green
  without a green run.
- Postgres via `docker-compose up -d db` on host port 5433.
