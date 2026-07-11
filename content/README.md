# Insight pack content

This directory holds the **insight pack catalogue** as versioned content
(WP 0.5). Packs are **data, not code**: adding or revising a pack means adding
a JSON file here, validating it, and loading it into the database — no
application changes.

> **DRAFT WORDING — pending review.** All question wording, options and scale
> statements in `packs/` are drafts written for scaffolding and preview
> purposes. They must be reviewed by Marc against the real Culture Counts
> question banks and quality-dimension statements before any pack is used for
> a live survey (roadmap: WP 0.5 input, gates WP 2.1/2.2). The Culture Counts
> dimension statements in `audience-experience` are best-effort approximations
> of the standard bank, not confirmed text.

## Layout

```
content/
  README.md                     <- this file
  schema/pack.schema.json       <- JSON Schema (draft 2020-12) for a pack version file
  packs/<slug>/v<N>.json        <- one file per pack version
  validate.py                   <- schema + referential-integrity validator
```

Launch catalogue: `audience-experience` (quality), `impact-outcomes` (impact),
`visitor-feedback` (feedback), `audience-profile` (profile).

## Versioning rules

- A pack version file is **immutable once published** (i.e. once any
  `template_versions` row referencing it exists in a shared environment).
  Any change — wording, question order, chart set, sample data — is a new
  `v<N+1>.json`. This is what makes responses comparable over time: a response
  is always interpretable against the exact manifest it was collected under.
- `slug` must equal the directory name; `version` must equal the `N` in the
  file name. `validate.py` enforces both.

## How packs flow through the system

Per `docs/02-architecture.md`, the DB models packs as `survey_templates`
(one row per pack) and `template_versions` (one row per version). The loader
(seed/sync command, owned by `api/`) maps a file onto those tables 1:1:

| File field | DB column |
|---|---|
| `slug`, `name`, `focus`, `description` | `survey_templates.slug / name / focus / description` |
| `version` | `template_versions.version` |
| `question_manifest` | `template_versions.question_manifest` (jsonb) |
| `insight_spec` | `template_versions.insight_spec` (jsonb) |
| `sample_dataset` | `template_versions.sample_dataset` (jsonb) |
| `headline_questions` | catalogue display; store alongside the template (suggested: in `survey_templates` or the version jsonb — loader's choice, but the catalogue card reads it) |

`template_versions.engine_survey_ref` is **not** in these files: it is
assigned at runtime when the Culture Counts adapter calls `ensure_survey()`
for a version.

Downstream consumers:

1. **Catalogue & pack preview (WP 2.1)** renders the pack page entirely from
   this file: `headline_questions` + `focus` badge on the card;
   `sample_dataset` drives the example charts and example narrative;
   `question_manifest` renders the collapsed "questions this answers" list.
2. **Survey engine (WP 2.2)** creates/ensures the Culture Counts survey from
   `question_manifest`.
3. **Ingestion (WP 4.2)** stores `responses.answers` keyed by manifest
   question `id`.
4. **Insight generation (WP 5.1/5.2)** computes each `insight_spec` block from
   real responses (with box-office cuts), then calls the LLM with the
   aggregates + free-text answers + `narrative_prompt`.

## Pack file format

Normative definition: `schema/pack.schema.json` (every property has a
`description`). Summary:

### Metadata

- `slug`, `name`, `version`, `focus` (`quality | impact | feedback | profile`),
  `description`.
- `headline_questions` — 2–5 plain-English questions the pack answers about an
  audience ("Was it good — and would your audience recommend it?"). Shown in
  the catalogue; this is the insight-first pitch, keep them outcome-phrased.

### `question_manifest`

Ordered array (array order = presentation order). Each question:

- `id` — snake_case, unique in the pack, stable across versions when the
  question is unchanged (it is the join key for responses and insight blocks).
- `type` — `likert_5 | likert_7 | nps | single_choice | multi_choice |
  free_text | demographic`. `demographic` behaves like `single_choice` but is
  flagged so UIs can treat personal questions appropriately (e.g.
  "prefer not to say" handling, placement at the end of the survey).
- `prompt` — respondent-facing text.
- `required` — whether the respondent must answer.
- `options` — required for `single_choice`, `multi_choice`, `demographic`;
  forbidden otherwise.
- `scale_labels` — optional label override for likert questions (must match
  the scale length). Default labels when absent:
  - `likert_5`: Strongly disagree / Disagree / Neither agree nor disagree /
    Agree / Strongly agree
  - `likert_7`: adds Somewhat disagree / Somewhat agree around the midpoint.
- `dimension` — optional Culture Counts quality-dimension key
  (`captivation`, `challenge`, `distinctiveness`, `enthusiasm`, `relevance`,
  `rigour`, ...). Likert questions only. Enables cross-event dimension
  benchmarking later.
- NPS questions are always 0–10, "not at all likely" to "extremely likely".

### `insight_spec`

- `narrative_prompt` — pack-level instruction for the LLM narrative section.
  The insight job (WP 5.2) supplies it together with the computed block
  aggregates and free-text answers; the narrative may only cite numbers
  present in those aggregates.
- `settle` — when the report may be generated:
  - `days_after_last_send` — trigger this many days after the last send
    (invite or reminder) unless generated manually (default posture: 7).
  - `min_responses` — below this, generate with a prominent low-sample caveat
    rather than full narrative confidence.
- `blocks` — 4–7 ordered chart/metric blocks. Each:
  - `id` — snake_case, unique in the pack.
  - `kind` — `metric_tile | bar | stacked_bar | line | distribution |
    theme_list | quote_list`.
  - `title` — rendered heading.
  - `question_ids` — manifest ids the block draws from.
  - `cut` — optional box-office cut: `none` (default) |
    `first_timer_vs_regular` | `donor_vs_non_donor` | `booking_lead_time`.
    A cut block renders the same chart segmented by the box-office attribute —
    the enrichment only this product can do. This enum is shared with the
    WP 5.1 aggregate computation; extending it means extending 5.1.
  - `measure` (+ `option_label`) — `metric_tile` only: how the single
    referenced question becomes one number.
    - `nps` — NPS score (nps questions).
    - `mean` — mean scale point, e.g. 4.07/5 (likert).
    - `top_two_box_share` — share answering the top two scale points (likert).
    - `option_share` — share choosing `option_label` (choice/demographic).
  - `notes` — authoring note, not rendered.

**Kind ↔ question-type rules** (enforced by `validate.py`):
`theme_list`/`quote_list` draw only from `free_text`; all other kinds draw
only from non-free-text questions. Rendering conventions for the quantitative
kinds: with multiple `question_ids`, `bar` shows one summary bar per question
(mean for likert) and `stacked_bar` one full distribution row per question;
with a single choice question, `bar` shows one bar per option;
`distribution` is a single-question histogram (all 11 NPS buckets, or all
scale points/options). `line` is reserved for time-series (e.g. responses or
scores over time) — no launch pack uses it yet.

### `sample_dataset` — **canonical aggregate shape**

The sample dataset is **precomputed aggregates, not raw response rows**, plus
curated free-text snippets:

```jsonc
"sample_dataset": {
  "response_count": 243,
  "questions": {                       // one entry per manifest question, exactly
    "exp_captivation": {               // likert / choice / demographic
      "type": "distribution",
      "labels": ["Strongly disagree", ..., "Strongly agree"],  // == options / scale labels
      "counts": [3, 8, 27, 104, 101],  // labels[i] pairs with counts[i]
      "answered": 243                  // optional; REQUIRED for multi_choice,
    },                                 // where counts may sum past answered
    "exp_nps": {
      "type": "nps",
      "counts_by_score": {"0": 1, ..., "10": 61},  // all 11 buckets
      "score": 38                      // round(100*(promoters-detractors)/total), cross-checked
    },
    "exp_open": {
      "type": "free_text",
      "answered": 131,
      "snippets": ["...", "..."]       // 5-25 curated example answers
    }
  },
  "cuts": {                            // one entry per cut used by any block
    "first_timer_vs_regular": {
      "segments": [
        { "key": "first_timer", "label": "First-time attenders",
          "n": 87, "share": 0.36,      // share consistent with n (±0.02)
          "questions": { /* same aggregate shapes, capped at n, no free_text */ } }
      ]
    }
  },
  "example_themes": [                  // required iff a theme_list block exists
    { "label": "...", "mentions": 31, "quotes": ["..."] }
  ],
  "example_narrative": {               // preview stand-in for the LLM output
    "headline": "...", "key_findings": ["..."], "caveats": ["..."]
  }
}
```

**Why aggregates?** The preview UI (WP 2.1) maps `labels`/`counts` straight
onto chart props with zero client-side statistics; distributions are
hand-tuned to look plausible; files stay small; and cut segments are
precomputed so the box-office-cut blocks render without any join logic.

**Canonical contract.** These aggregate shapes (`distribution`, `nps`,
`free_text`, and `cuts.segments`) are the contract between content, the
preview UI, and the real pipeline:

- The **WP 2.1 preview** renders `sample_dataset` as if it were a computed
  result for a real event.
- The **WP 5.1 aggregation job** must produce this same structure from raw
  `responses.answers` (per question, and per segment for each cut a block
  requests). Then WP 4.4/5.3 chart components consume one shape everywhere —
  preview and real report use identical rendering code.
- Real-pipeline-only concerns layer on top without changing the shape:
  minimum-cell-size suppression (WP 5.1 drops segments with n < 10),
  respondent-sourced `snippets` for quote lists, and LLM output replacing
  `example_themes` / `example_narrative` (which are preview-only stand-ins and
  **not** part of the production report contract — the report's themes and
  narrative come from `insight_reports.narrative`).

Arithmetic invariants (enforced by `validate.py`): single-select counts sum to
at most `response_count` (segment counts to at most the segment `n`);
`answered`, when present, equals the sum for single-select and caps every
per-option count for multi-select; NPS `score` matches its buckets; segment
`share`s are consistent with `n` and sum to ~1.

Sample datasets should represent roughly 150–400 responses — big enough that
the preview charts look like a real event, small enough to stay believable for
a single performance.

## Validation

```
python3 content/validate.py                                   # integrity checks (stdlib only)
uv run --no-project --with jsonschema python3 content/validate.py   # + full JSON Schema validation
```

`validate.py` exits non-zero on any failure. It validates every
`packs/*/v*.json` against the schema (when `jsonschema` is installed) and
always cross-checks referential integrity: block `question_ids` exist,
kind ↔ question-type compatibility, `measure` semantics, sample-dataset
coverage of every question, cut coverage and segment arithmetic, NPS score
recomputation, label/option matching, slug/version ↔ path agreement, and
`example_themes` ⇔ `theme_list` pairing. Run it in CI and before seeding
packs into any environment.

## Authoring checklist for a new pack version

1. Copy the previous version to `v<N+1>.json`, bump `version`.
2. Keep `id`s stable for unchanged questions; new/changed questions get new ids.
3. Update `insight_spec` blocks and, if you add a cut, add matching
   `sample_dataset.cuts` segments.
4. Re-tune `sample_dataset` so the preview reflects the new questions.
5. `python3 content/validate.py` until green; get wording reviewed (Culture
   Counts question bank) before the version is published.
