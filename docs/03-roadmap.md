# Development Roadmap — Auto Insight

Six phases. Each work package (WP) is scoped to be handed to a subagent: it
names its inputs, outputs, and acceptance criteria, and assumes the
architecture in `02-architecture.md`. Phases are sequential; WPs within a
phase can mostly run in parallel unless a dependency is noted.

A **non-code track** for Marc runs alongside (bottom of this doc).

---

## Phase 0 — Foundations

**Goal**: a deployed, tested, multi-tenant skeleton a pilot user can log into.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **0.1 Repo scaffold** | Monorepo: `api/` (FastAPI, SQLAlchemy 2, Alembic, Procrastinate), `web/` (Vite + React + TS, TanStack Query/Router), `docs/`. Ruff + mypy + pytest; ESLint + Prettier + Vitest. Docker Compose for local Postgres. | `make dev` brings up api+web+db locally; `make test` green in CI |
| **0.2 Baseline schema & tenancy layer** | Alembic migration for all tables in `02-architecture.md` §Data model. `OrgContext`-scoped repository layer; tests proving cross-org reads are impossible through it. | Migration applies clean; tenancy tests pass |
| **0.3 Auth & org membership** | Email + password with secure session cookies, password reset by email, `member`/`admin` roles, org switcher for internal staff accounts. No self-serve signup — orgs and users seeded by CLI command. | Seeded admin logs in, sees empty app shell, role gates enforced |
| **0.4 Deploy pipeline** | Decide AWS runtime (App Runner vs ECS Fargate — pick simplest that runs api+worker), Terraform or CDK for infra, GitHub Actions CD to staging on merge, manual promote to production. Secrets in SSM/Secrets Manager. | Merge to main → staging updated; documented promote step |
| **0.5 Insight pack content: launch catalogue** | Author the 4 packs from the brief as versioned content: question manifest, insight spec (charts/metrics/narrative prompt), realistic sample dataset for previews. Content format documented so packs are data, not code. Requires Culture Counts question/dimension input from Marc. | 4 packs load from fixtures; schema-validated; sample data renders the preview charts in Storybook or a dev page |

**Phase exit**: a logged-in user in a seeded org sees the app shell on staging.

---

## Phase 1 — Box office connection & data browser

**Goal**: a pilot org connects real Spektrix credentials and sees their own
events and audiences. Immediate value before any survey exists.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **1.1 Spektrix adapter** | Implement `BoxOfficeProvider` for Spektrix: auth, pagination, rate-limit handling, `test_connection`, iterators for events/instances/attendances/customers/tags/contact-preferences. Port lessons (not code wholesale) from the existing data-warehouse connector. Record/replay fixtures for tests. | Adapter passes contract tests against fixtures; `test_connection` distinguishes bad creds from network errors |
| **1.2 Sync engine** | Procrastinate recurring job per connection; incremental cursors; idempotent upserts; contact preferences → `opted_out_at` + suppressions; sync heartbeat + error state on the connection row. | Two consecutive syncs of same fixture data are a no-op; interrupted sync resumes without duplicates |
| **1.3 Connect flow UI** | Admin enters Spektrix credentials → `test_connection` → save (encrypted) → first sync kicks off with progress/status display and clear failure messages. | Bad credentials rejected with actionable message; good ones show sync progress then data |
| **1.4 Data browser UI** | Events list (upcoming/past, attendance counts, search); event detail with instances; audience view (customers with tags, filterable: donors, first-timers, regulars); sync status banner. | Pilot-scale data (tens of thousands of customers) pages smoothly; tag filters correct against fixtures |

**Phase exit**: real pilot org connected on production; their events and
audience browsable; sync self-heals overnight.

---

## Phase 2 — Insight pack catalogue & allocation

**Goal**: the signature insight-first experience — browse packs by the insight
they produce, allocate one to an event in a few clicks.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **2.1 Catalogue & pack preview UI** | Catalogue grid with focus badges; pack page leads with the **example insight report** rendered from `sample_dataset` (charts + example narrative + "questions this answers"), question list collapsed below. This page is the product's shop window — polish matters. | All 4 packs render previews from sample data; question list matches manifest exactly |
| **2.2 Culture Counts engine adapter** | Implement `SurveyEngine` for CC: ensure a CC survey exists per template version (`ensure_survey`), build invite links embedding the hidden token (`build_invite_link`). Spike first: confirm with Marc how survey creation/reuse works in CC (one shared survey per template version vs per org). | Generated link opens correct CC survey; token round-trips (visible in a test submission) |
| **2.3 Allocation flow** | From an event or from a pack: pick pack ↔ pick event(s), configure send delay (default: next morning after final performance… default per-instance +18h), reminder on/off. Allocation summary shows estimated eligible audience size (uses Phase 3 eligibility rules in preview mode; until 3.1 lands, show raw attendee count with a note). Cancel/edit before first send. | Allocation created in ≤ 3 clicks from event page; invitations not yet created (that's the send pipeline's job) |
| **2.4 Allocations dashboard** | List of allocations with status (scheduled/sending/collecting/complete), upcoming sends timeline. | Statuses reflect pipeline state machine; empty states explain what happens next |

**Phase exit**: user allocates a pack to a future event; a scheduled send is
visible; links resolve to the right CC survey with token intact.

---

## Phase 3 — Automated distribution ⚠ highest-risk phase

**Goal**: a real performance triggers a fully automated, compliant send with
zero human steps.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **3.1 Eligibility engine** | Implement the eligibility query from `02-architecture.md`: attendees minus no-email / box-office opt-out / suppression list / frequency cap (org-configurable, default 30 days). Every exclusion recorded as a `suppressed` invitation with reason. | Property-style tests: no suppressed or capped customer ever reaches `pending`; exclusion reasons auditable per send |
| **3.2 SES integration & sender identities** | `EmailProvider` for SES; configuration sets; SNS webhook endpoint normalising delivery/bounce/complaint into `email_events`; bounces/complaints → immediate suppression + invitation status flip. Per-org sender identity setup (subdomain, DKIM) as a documented runbook executed with each pilot org. | Sandbox end-to-end test: send → delivery event recorded; simulated bounce suppresses future sends to that address |
| **3.3 Send pipeline & scheduler** | Scheduler job creates invitations post-instance per allocation config; send job with batching, retries, idempotency (an invitation is never sent twice — enforce with status transitions + unique constraint on send attempt); reminder job (default +3 days, once, only status `sent`). | Kill the worker mid-batch, restart: no duplicate emails (verified via provider message IDs in tests); reminders never go to responders/bounces |
| **3.4 Invitation email template & unsubscribe** | One locked, research-only, mobile-tested email template (org branding slots: name, logo, colour). `List-Unsubscribe`/`List-Unsubscribe-Post` headers + tokenised one-click unsubscribe page → suppression + confirmation. Plain-text alternative part. | Renders in major clients (Litmus-style checklist); unsubscribe from a real email suppresses within seconds; no promotional content slots exist |
| **3.5 Send monitoring UI** | Per-allocation send report: eligible/sent/delivered/bounced/complained/unsubscribed counts, exclusion-reason breakdown, per-recipient status table (email shown, no other PII), alert states (complaint rate > 0.1%, bounce > 2% → pause sends for that org + notify us). | Numbers reconcile exactly with `invitations` + `email_events`; alert pause verified by test |

**Phase exit**: a real pilot performance produces an automated send;
suppression honoured end-to-end; monitoring reconciles; complaint/bounce
alarms tested.

---

## Phase 4 — Response collection & live dashboard

**Goal**: responses appear, joined to customers and events, within minutes of
submission.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **4.1 CC response retrieval spike** | Time-boxed: confirm mechanism (API vs export), auth, latency, and token fidelity for pulling responses. Output: a short doc + go/no-go on polling interval. **Blocks 4.2.** | Written findings; test response retrieved and matched to its token |
| **4.2 Ingestion job** | Recurring pull per active survey; token → invitation join; `answers` stored per the pack's question manifest; invitation status → `responded`; orphan tokens logged, never dropped silently. | Idempotent re-pull; malformed/partial responses quarantined with alert, pipeline continues |
| **4.3 Live dashboard** | Org home becomes "data coming in": per-allocation response rate vs sends, response curve over time, recent-responses feed (anonymous), org-level totals. | Response submitted in CC visible on dashboard within one polling interval; rates match DB exactly |
| **4.4 Basic per-event results** | Pre-insight-report view: per-question aggregates (choice distributions, rating averages) rendered from the same insight-spec chart components as the pack previews (reuse WP 2.1 components). | Charts match hand-computed aggregates on fixture responses |

**Phase exit**: pilot event collects real responses visible live on the
dashboard, joined to box office attributes in the DB.

---

## Phase 5 — Insight reports

**Goal**: the payoff — a funder-ready report generated automatically per
allocation, combining charts with LLM narrative and box-office enrichment.

| WP | Scope | Acceptance criteria |
|---|---|---|
| **5.1 Enriched aggregate computation** | Compute the insight spec's metrics with box office cuts: first-timer vs regular, donor vs non-donor, booking lead time, tag-based segments. Minimum-cell-size rule (suppress cuts with n < 10) to avoid identifying individuals. | Deterministic outputs on fixtures; small cells suppressed; all cuts computed in one pass per allocation |
| **5.2 LLM narrative generation** | Claude API with structured output: input = computed aggregates + free-text answers + pack's narrative prompt; output = key findings, themes with representative quotes, comparisons, caveats (sample size, response rate). Guardrails: narrative may only cite numbers present in the input aggregates; retry/validation on schema mismatch; per-org token spend logging. | Narrative validates against schema; spot-check on fixtures shows no fabricated numbers (validator cross-checks every cited figure) |
| **5.3 Report page & PDF export** | Report route assembling charts (WP 2.1/4.4 components) + narrative sections; shareable internally; print-quality PDF export (server-side render). | Report for a fixture allocation matches design; PDF paginates cleanly with charts |
| **5.4 Report lifecycle & notification** | Insight job triggers when responses settle (default 7 days after last send, or manual "generate now"); status on allocations dashboard; "your insight report is ready" email to org users (this one is operational, not research — separate template). | End-to-end on staging: allocation → send → responses → report ready email with working link |

**Phase exit**: a completed pilot event produces a report an org shows to its
board/funder without editing. This is the pilot's success moment.

---

## Phase 6 — Post-pilot backlog (listed, not specced)

Prioritise from pilot learnings:

- Self-serve onboarding (Spektrix connect + automated sender-domain setup) and billing
- Allocation rules: "all events tagged X get pack Y" (turns the product fully hands-off)
- Response-rate benchmarking and cross-org comparison (aggregate, anonymised)
- Additional box office providers (Tessitura, Ticketsolve) via `BoxOfficeProvider`
- Additional survey engines via `SurveyEngine` (org chooses look/feel)
- Season/portfolio-level reports (across allocations), year-on-year trends
- SMS distribution channel; embedded post-purchase surveys

---

## Dependency notes

- 0.5 (pack content) needs Marc's input on Culture Counts questions/dimensions — start early, it gates 2.1 and 2.2.
- 2.2 and 4.1 both involve Culture Counts platform specifics — do the 2.2 spike and 4.1 spike together if possible.
- 3.2 SES production access has AWS-side lead time (support case + warm-up) — request as soon as Phase 3 starts, not when it's needed.
- Phase 4 can begin while Phase 3 hardening finishes; Phase 5 WP 5.1/5.2 can be built against fixture responses before real data exists.

## Non-code track (Marc, parallel)

| When | Item |
|---|---|
| Phase 0 | Confirm pilot orgs (2–5); pick product name; provide CC question sets for the 4 packs |
| Phase 1 | Pilot org Spektrix API credentials + data-sharing sign-off |
| Phase 2 | DPA template + privacy notice drafted (legal review) |
| Phase 3 | Per-org sender subdomain DNS with each pilot org's IT; SES production access request; ESP warm-up schedule |
| Phase 5 | Review first generated narratives with pilot orgs; funder-report feedback loop |
