# Product Brief — Auto Insight

## One-line pitch

Connect your box office once, pick the insight you want about your audiences,
and it arrives automatically after every event — no survey design, no email
scheduling, no spreadsheet wrangling.

## The problem

Arts organisations know they should measure audience experience and impact, and
funders increasingly require it. But the workflow is miserable for a
resource-starved marketing/development team: design a survey, build an email,
export an audience list, send it at the right moment, chase responses, then
analyse a CSV. Most organisations either don't do it, do it once a year, or do
it inconsistently so the data can't be compared across events.

## The insight-first inversion

Every existing tool starts the user at "build your survey". We start them at
**the insight the survey produces**. The catalogue is a set of **insight
packs**: each one is presented first as an example dashboard — realistic
charts, an LLM-written analysis, the questions it answers about your audience —
with a clear focus badge (Quality Assessment, Impact Measurement, Audience
Feedback, Audience Profile). The question set is visible underneath for review,
but the user's decision is "which of these answers do I want about this
event?", not "what should question 4 be?".

## The core loop

1. **Connect** — organisation connects Spektrix (API credentials). We sync
   their events, performances, ticket buyers, and customer tags (donor, member,
   regular attender, ...).
2. **Choose** — they browse the insight pack catalogue and review example
   insight, then the underlying questions.
3. **Allocate** — they assign a pack to one or more events (later: rules like
   "every event tagged Drama gets the Experience pack").
4. **Automatic from here** — after each performance the platform selects
   eligible attendees (consent flags, suppressions, frequency caps), generates
   per-customer Culture Counts survey links with a hidden respondent token,
   sends branded invitation emails (plus an optional reminder), and ingests
   responses as they arrive.
5. **Insight arrives** — a live dashboard shows data coming in; once responses
   settle, the platform generates the event's insight report: the pack's charts
   populated with real data plus LLM narrative analysis, enriched with box
   office context the org could never get from a survey alone (first-timers vs
   regulars, donors vs non-donors, booking lead time).

The enrichment in step 5 is the durable moat: because we hold the
customer–response join, every chart can be cut by box office attributes.
"Audiences rated it 4.5/5" is a survey product; "first-time attenders rated it
significantly lower than regulars, and they were 40% of the house" is this
product.

## Users

- **Primary**: marketing / audience development managers at small-to-mid arts
  organisations using Spektrix (UK-heavy install base).
- **Secondary**: development/fundraising teams (donor sentiment), executive
  directors (board and funder reporting).
- **Pilot**: 2–5 known Spektrix organisations, onboarded by hand. We do the
  DNS/sender setup with them, warm sending domains slowly, and sign a DPA as
  part of onboarding.

## Launch insight pack catalogue (draft)

| Pack | Focus badge | Answers questions like |
|---|---|---|
| Audience Experience | Quality Assessment | Was it good? Would they recommend it? How does it compare to your other events? Uses Culture Counts quality dimensions. |
| Impact & Outcomes | Impact Measurement | Did it move people? Did they learn or feel challenged? Funder-ready impact evidence. |
| Visitor Feedback | Audience Feedback | What did they love, what frustrated them, what would they change? Free-text heavy, theme extraction. |
| Audience Profile | Audience Profile | Who came? Demographics, how they heard about it, first-timer share. |

Packs are versioned content, not code: question manifest + insight spec
(charts, metrics, narrative prompts) + sample dataset for the preview.

## Compliance posture (decided)

- We are a **data processor** for each organisation. DPA signed at onboarding;
  documented retention policy; suppression of anyone opted out in Spektrix.
- Invitation emails are strictly **research-only** content (no promotional
  material) so they sit on the market-research side of the PECR direct-marketing
  line. This is a hard rule enforced by the template system, not editorial
  judgement per email.
- Culture Counts receives only a pseudonymous respondent token, never the
  customer's identity. The token→customer mapping lives only in our database.
- One-click unsubscribe in every email; unsubscribes, bounces, and complaints
  feed an org-level suppression list immediately.
- Frequency capping is a product feature: default, a customer is surveyed at
  most once every 30 days per organisation (configurable).

## What success looks like for the pilot

- ≥ 80% of allocated performances result in a completed automated send with
  zero human intervention.
- Response rates comparable to or better than the orgs' historical manual
  efforts (post-event survey norms are roughly 5–15% of attendees).
- Spam complaint rate < 0.1%, bounce rate < 2% after list hygiene.
- At least one pilot org uses a generated insight report in a funder
  application or board pack — the "this replaced real work" signal.
- Qualitative: orgs describe allocation as "a couple of clicks", and review the
  insight, not the questions.

## Open questions (tracked, not blocking)

1. **Product name** — "Auto Insight" is a working title.
2. **Culture Counts response retrieval** — confirm the mechanism (API vs
   export) and latency for pulling responses keyed by hidden token. Phase 4
   spike.
3. **Hosting** — ~~SES for email pushes toward AWS; final call in Phase 0.~~
   **Decided 2026-07-12**: DigitalOcean (App Platform + Managed Postgres),
   with Postmark as the email provider — see `infra/README.md` and
   `docs/02-architecture.md`.
4. **Reminder emails** — one reminder to non-responders is standard and
   roughly doubles response volume; confirm we're comfortable with the PECR
   posture (still research-only content). Default: on, 3 days after invite.
5. **Response data residency** — decided assumption: raw submissions live in
   Culture Counts; we ingest answer data (keyed by token) into our DB for
   analysis and enrichment. Revisit only if a pilot org objects.
