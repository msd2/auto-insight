# Auto Insight (working title)

Automated audience insight for arts organisations. Connect your box office system,
allocate an insight pack to your events, and the platform handles everything else:
survey distribution after each event, response collection, and analysis — so
organisations skip survey design and go straight to insight.

Built by Culture Counts as a product alongside the existing survey platform.

## Documents

| Doc | Purpose |
|---|---|
| [docs/01-product-brief.md](docs/01-product-brief.md) | What we're building, for whom, and the decisions already made |
| [docs/02-architecture.md](docs/02-architecture.md) | System design, integrations, data model |
| [docs/03-roadmap.md](docs/03-roadmap.md) | Phased delivery plan broken into work packages for subagents |

## Locked decisions

- **Stack**: Python (FastAPI) backend, React + TypeScript frontend, Postgres.
- **Distribution**: the platform sends survey invitation emails itself (full
  automation is the product). Consent handling, suppression sync, and
  deliverability are first-class Phase 3 scope, not afterthoughts.
- **Go-to-market**: pilot with 2–5 hand-onboarded Spektrix organisations first;
  self-serve SaaS later. Schema is multi-tenant from day one.
- **Insight at launch**: pre-built charts per template **plus** LLM-generated
  narrative analysis (key findings, free-text themes, plain-English commentary).
- **First integrations**: Spektrix (box office, API connection already proven via
  data warehouse work) and Culture Counts (survey collection, per-respondent
  hidden-ID links). Both behind adapter interfaces so more can follow.
