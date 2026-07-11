# STATUS — Phase 0 execution handoff

Last updated: 2026-07-11 (context handoff during Phase 0, wave 1).
Read `CLAUDE.md` first if you haven't. This doc is the live state of Phase 0
(`docs/03-roadmap.md`) and must be updated whenever a work package lands.

## Where things stand

| WP | Task # | State |
|---|---|---|
| 0.1 Repo scaffold | #1 | **IN FLIGHT** — a background agent was mid-build at handoff. See "WP 0.1 takeover" below. |
| 0.2 Schema & tenancy | #2 | Not started (wave 2) |
| 0.3 Auth & membership | #3 | Not started (wave 2) |
| 0.4 Deploy pipeline authoring | #4 | Not started (wave 2). AWS *deployment* is blocked on account/credentials — authoring only for now. |
| 0.5 Pack content | #5 | **DONE**, committed `ecd4e8a`. Preview UI wiring remains (wave 2, agent C). |

Git: branch `main`, remote `origin` = github.com:msd2/auto-insight (push
after each checkpoint). Commits so far: `c79266c` (planning docs, by Marc),
`ecd4e8a` (wp0.5 content), `41256fe` (handoff docs). Convention: one
checkpoint commit per verified WP, message prefix `wp<N.n>:`.

## WP 0.1 takeover instructions

The prior session's background agent may or may not have finished after this
doc was written. **First**: `git status` + inspect the tree, then diff against
the full WP 0.1 spec below. Complete whatever is missing, then run the
verification suite regardless of who wrote the code.

Spec (agreed, plan-approved): monorepo with
- `api/` — FastAPI app factory (`autoinsight/main.py`), pydantic-settings
  `config.py` (DATABASE_URL-driven; Procrastinate DSN derived from same URL),
  async SQLAlchemy 2 `db.py`, `GET /health` (always 200, reports
  `database: "ok"|"unavailable"`), `worker.py` (Procrastinate wired, no jobs),
  empty `models/` + `repositories/` packages, Alembic (async template,
  `target_metadata = None`, no migrations yet), pyproject managed by `uv`
  (deps: fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic,
  procrastinate[psycopg], pydantic-settings; dev: pytest, pytest-asyncio,
  httpx, ruff, mypy), one /health test via httpx ASGITransport with DB
  dependency overridden.
  Status at handoff: `autoinsight/` package written (main/config/db/worker/
  health); **missing: Alembic init, tests/, uv.lock/venv check**.
- `web/` — **entirely missing at handoff.** Vite + React 18 (^18.3, not 19) +
  TS; @tanstack/react-query + react-router (code-based routes, no codegen);
  recharts (dependency only); `/login` placeholder route + authed AppShell
  layout (sidebar: Dashboard, Events, Surveys, Reports; org-name placeholder
  in header); ESLint flat + Prettier + Vitest/jsdom + Testing Library with an
  AppShell smoke test; `src/api/client.ts` typed fetch wrapper at `/api`;
  Vite dev proxy → localhost:8000.
- Root — **missing at handoff**: docker-compose.yml (postgres:16 only, host
  port **5433**, volume, pg_isready healthcheck), Makefile (dev-db/dev-api/
  dev-web/dev/test/lint/fmt), .gitignore, .env.example
  (`DATABASE_URL=postgresql+asyncpg://autoinsight:autoinsight@localhost:5433/autoinsight`),
  `.github/workflows/ci.yml` (api job with postgres service: ruff/mypy/pytest;
  web job on Node 22: eslint/tsc/vitest/build).

Verification (all must pass before the wp0.1 commit): `make lint`,
`make test`, `cd web && npm run build`, boot uvicorn + curl /health, and with
Docker up: compose db healthy + /health reports `database: "ok"`.
Toolchain on this machine: uv ✓, Python 3.14.4 (target 3.12+; pin uv to 3.12
if a dep lacks 3.14 wheels), Node 25/npm 11 (CI uses Node 22), Docker ✓.

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
