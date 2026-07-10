# Architecture — Auto Insight

## Overview

Three deployable pieces sharing one Postgres database, plus adapter layers for
every external system so integrations can be added without touching core code.

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│  web (SPA)  │────▶│  api (FastAPI)                           │
│  React + TS │     │  auth · tenancy · REST endpoints         │
└─────────────┘     └──────────────┬───────────────────────────┘
                                   │ SQLAlchemy
                    ┌──────────────▼───────────────┐
                    │  Postgres 16                 │
                    │  app schema + job queue      │
                    └──────────────▲───────────────┘
                                   │ Procrastinate (Postgres-backed jobs)
                    ┌──────────────┴───────────────────────────┐
                    │  worker                                  │
                    │  sync · eligibility · send · ingest ·    │
                    │  insight generation                      │
                    └───┬──────────┬──────────┬──────────┬─────┘
                        ▼          ▼          ▼          ▼
                    Spektrix   Culture     AWS SES    Claude API
                     (API)     Counts     (+ SNS       (LLM)
                               (API)     webhooks)
```

## Stack decisions

| Concern | Choice | Rationale |
|---|---|---|
| API | FastAPI + SQLAlchemy 2 + Alembic, Python 3.12 | Locked decision; async-friendly, typed, well known to agents |
| DB | Postgres 16 | One datastore for app data **and** job queue |
| Jobs | Procrastinate | Postgres-backed queue with cron/scheduled jobs; no Redis/broker to run during the pilot. If it ever limits us, the job functions port to Celery unchanged. |
| Frontend | Vite + React + TypeScript, TanStack Query + Router, Recharts | Locked decision; Recharts covers the launch chart set |
| Email | AWS SES with configuration sets; SNS → webhook for delivery/bounce/complaint events | Cheapest at volume, per-org sender identities, mature suppression tooling |
| LLM | Claude API (structured outputs) | Narrative generation + free-text theme extraction |
| Hosting | AWS (single environment for pilot; ECS Fargate or App Runner) | SES already pulls us to AWS; final sizing is a Phase 0 work package |

## Multi-tenancy

Single database, shared schema. Every tenant-owned table carries a non-null
`org_id` FK. All queries go through a repository/service layer that requires an
`OrgContext` — no endpoint handler touches a session directly, so "forgot the
org filter" is structurally hard. Pilot has a handful of orgs but nothing in
the schema needs to change for self-serve later.

Roles for the pilot: `member` and `admin` per org (admin can manage the box
office connection and users). Cross-org access does not exist.

## Integration adapters

Each external system sits behind a small interface so the second
implementation is an adapter, not a rewrite:

- **`BoxOfficeProvider`** — `test_connection()`, `iter_events(since)`,
  `iter_instances(since)`, `iter_attendances(instance)`,
  `iter_customers(since)`, `get_contact_preferences(customer)`.
  First impl: **Spektrix** (REST API, per-client credentials — reuse patterns
  from the existing data-warehouse connector).
- **`SurveyEngine`** — `ensure_survey(template_version)`,
  `build_invite_link(survey, token)`, `iter_responses(survey, since)`.
  First impl: **Culture Counts** (links embed the hidden token; responses are
  retrieved keyed by that token — retrieval mechanism confirmed by a Phase 4
  spike).
- **`EmailProvider`** — `send(message) -> provider_message_id`, plus a webhook
  handler that normalises delivery/bounce/complaint events.
  First impl: **SES**.

## Data model (draft)

PII policy: we store the minimum needed to send and join — external customer
ID, email, first name, tags. Culture Counts only ever sees the opaque token.
Raw response submissions live in Culture Counts; we ingest answer data for
analysis (decided assumption, brief §Open questions).

```
organisations        id, name, slug, sender_domain, settings jsonb
users                id, org_id, email, name, role, auth fields
box_office_connections id, org_id, provider ('spektrix'), credentials (encrypted),
                     status, last_synced_at

events               id, org_id, external_id, name, description, tags jsonb
event_instances      id, event_id, external_id, starts_at, venue_name, capacity
customers            id, org_id, external_id, email, first_name,
                     opted_out_at (from box office preferences), created_at
customer_tags        customer_id, tag            -- donor, member, regular…
attendances          id, org_id, instance_id, customer_id, tickets, booked_at

survey_templates     id, slug, name, focus ('quality'|'impact'|'feedback'|'profile'),
                     description
template_versions    id, template_id, version, question_manifest jsonb,
                     insight_spec jsonb, sample_dataset jsonb, engine_survey_ref
allocations          id, org_id, template_version_id, event_id (or instance_id),
                     send_delay_hours, reminder_enabled, status, created_by

invitations          id, org_id, allocation_id, customer_id, token (uuid, unique),
                     status ('pending'|'sent'|'reminded'|'responded'|
                             'bounced'|'suppressed'|'failed'),
                     sent_at, responded_at
email_events         id, invitation_id, type ('delivery'|'bounce'|'complaint'|
                     'open'), provider_message_id, payload jsonb, occurred_at
suppressions         id, org_id, email_hash, reason ('unsubscribe'|'bounce'|
                     'complaint'|'box_office_opt_out'), created_at

responses            id, org_id, invitation_id, engine_response_ref,
                     answers jsonb, submitted_at
insight_reports      id, org_id, allocation_id, status, charts_data jsonb,
                     narrative jsonb, generated_at
```

`invitations.token` is the only identifier that leaves our system toward the
survey engine. `suppressions.email_hash` lets us honour opt-outs even after a
customer row is deleted.

## Key flows

### Spektrix sync (recurring job, per connection)
Incremental by `lastUpdated`-style cursors: events → instances → attendances
(customers via purchases) → tags → contact preferences. Contact preferences
update `customers.opted_out_at` and insert `box_office_opt_out` suppressions.
Sync is idempotent (upsert on `org_id + external_id`) and records a
`last_synced_at` heartbeat surfaced in the UI.

### Post-event send pipeline
1. Scheduler finds instances where `starts_at + send_delay` has passed and an
   active allocation exists with no send yet.
2. **Eligibility**: attendees of that instance, minus: no email, opted out in
   Spektrix, on the suppression list, or surveyed by this org within the
   frequency cap window (default 30 days). Ineligible attendees get an
   `invitation` row with status `suppressed` + reason, so coverage is auditable.
3. Create `pending` invitations with fresh tokens; build CC links.
4. Send via `EmailProvider` using the org's sender identity; email content is
   a locked research-only template (org name, event name, link, unsubscribe).
5. Reminder job: after `reminder_delay` (default 3 days), re-send once to
   invitations still in `sent`.
6. SNS webhooks update `email_events`; bounces and complaints immediately
   insert suppressions and flip invitation status.

### Response ingestion & insight
A recurring job pulls new responses per active survey from the
`SurveyEngine`, joins on token → invitation → customer/event, and stores
answers. The live dashboard reads sends/responses directly. When an
allocation's response flow settles (default: 7 days after last send, or
manually triggered), an insight job renders the pack's `insight_spec` —
each chart computed from responses **enriched with box office cuts**
(first-timer vs regular, donor, booking lead time) — then calls Claude with
the computed aggregates + free-text answers to produce structured narrative
(key findings, themes with representative quotes, caveats). Output persists to
`insight_reports`; a notification email tells the org it's ready.

## Compliance mechanics (where the brief's rules live in code)

- Research-only emails: invitation templates are code-reviewed content in the
  repo; there is no per-org free-text email editing in the pilot.
- One-click unsubscribe: `List-Unsubscribe` + `List-Unsubscribe-Post` headers
  and a tokenised unsubscribe page → immediate suppression.
- Frequency cap enforced in the eligibility query, not the UI.
- `credentials` encrypted at rest (KMS or libsodium sealed box); DB access via
  least-privilege roles; audit trail = `invitations` + `email_events`.

## Environments

Pilot: `staging` + `production`, both on AWS; GitHub Actions CI (lint,
typecheck, tests, migrations check) and CD to staging on merge. SES starts in
sandbox against staging with verified test addresses; production access
requested during Phase 3 with a warm-up plan.
