# Auto Insight — agent guide

Automated audience insight for arts organisations: connect a box office
system (Spektrix first), allocate "insight packs" to events, and the platform
automates survey distribution (we send the emails), collection (Culture
Counts links with hidden per-invitation tokens), and analysis (charts + LLM
narrative). Built by Culture Counts. Currently in **Phase 0** of a 6-phase
roadmap.

## Read in this order

1. `docs/STATUS.md` — **current state, in-flight work, next actions.** Always
   start here; always update it when you land a work package.
2. `docs/03-roadmap.md` — the phase/work-package plan with acceptance
   criteria. Your assignment is a WP in here.
3. `docs/02-architecture.md` — components, adapter interfaces, data model,
   key flows. The schema and naming here are authoritative.
4. `docs/01-product-brief.md` — product rationale and compliance posture
   (read before touching anything user-facing or email-related).

## Layout

- `api/` — FastAPI + SQLAlchemy 2 (async) + Alembic + Procrastinate, managed
  with `uv` (run tooling as `uv run ...` inside api/).
- `web/` — Vite + React 18 + TypeScript, TanStack Query/Router, Recharts.
- `content/` — insight pack definitions (versioned JSON data, not code) +
  `pack.schema.json` + `validate.py`. See `content/README.md` for the format;
  its aggregate shapes are the canonical chart-data contract shared by
  preview UI and the future real-aggregation pipeline. Validate after any
  content change: `python3 content/validate.py` (full check:
  `uv run --no-project --with jsonschema python3 content/validate.py`).
- `docs/` — the four documents above.
- Root: `Makefile` (`dev-db`/`dev-api`/`dev-web`/`test`/`lint`/`fmt`),
  `docker-compose.yml` (Postgres 16 on host port **5433**), `.env.example`.

## Invariants (do not violate)

- **Tenancy**: every tenant-owned row has `org_id`; all data access goes
  through the `OrgContext`-scoped repository layer — endpoint handlers never
  touch a session directly.
- **External systems only via adapters**: `BoxOfficeProvider`,
  `SurveyEngine`, `EmailProvider`. No provider-specific code outside its
  adapter.
- **Privacy**: the survey engine (Culture Counts) only ever receives the
  opaque invitation token — never customer identity. We store minimal PII
  (external id, email, first name, tags).
- **Email compliance**: invitation email content is research-only, locked
  templates in the repo — no promotional slots, no per-org free-text editing.
  One-click unsubscribe → immediate suppression.
- **Packs are data**: published pack versions are immutable; changes mean a
  new version file. Chart components consume the canonical aggregate shapes.

## Conventions

- Remote: github.com:msd2/auto-insight. One checkpoint commit per verified
  work package, message prefix `wp<N.n>:`, pushed after verification.
- Verify a WP's acceptance criteria (listed in the roadmap) before calling it
  done; run the relevant `make` targets yourself — don't trust a green claim
  you didn't reproduce.
- Python 3.12+ (machine has 3.14; pin uv to 3.12 if wheels are missing).
  React 18, not 19. CI targets Node 22.
- Question wording in `content/packs/` is DRAFT pending Marc's sign-off — do
  not treat it as final copy.
