/**
 * Typed view of a pack version file (`content/packs/<slug>/v<N>.json`).
 *
 * The aggregate shapes (`DistributionAggregate`, `NpsAggregate`,
 * `FreeTextAggregate`, `CutSegment`) mirror the canonical chart-data contract
 * documented in `content/README.md`: the WP 5.1 aggregation job produces the
 * same structures from real responses, so the chart components consuming
 * these types are reused verbatim for real reports (WP 2.1 / 4.4 / 5.3).
 */

export type PackFocus = 'quality' | 'impact' | 'feedback' | 'profile'

export type QuestionType =
  'likert_5' | 'likert_7' | 'nps' | 'single_choice' | 'multi_choice' | 'free_text' | 'demographic'

export interface PackQuestion {
  id: string
  type: QuestionType
  prompt: string
  required: boolean
  options?: string[]
  scale_labels?: string[]
  dimension?: string
}

export type BlockKind =
  'metric_tile' | 'bar' | 'stacked_bar' | 'line' | 'distribution' | 'theme_list' | 'quote_list'

export type CutKey = 'none' | 'first_timer_vs_regular' | 'donor_vs_non_donor' | 'booking_lead_time'

export type MetricMeasure = 'nps' | 'mean' | 'top_two_box_share' | 'option_share'

export interface InsightBlock {
  id: string
  kind: BlockKind
  title: string
  question_ids: string[]
  cut?: CutKey
  measure?: MetricMeasure
  option_label?: string
  notes?: string
}

export interface InsightSpec {
  narrative_prompt: string
  settle: {
    days_after_last_send: number
    min_responses: number
  }
  blocks: InsightBlock[]
}

/** Likert / single_choice / multi_choice / demographic aggregate. */
export interface DistributionAggregate {
  type: 'distribution'
  /** One label per option / scale point; `labels[i]` pairs with `counts[i]`. */
  labels: string[]
  counts: number[]
  /**
   * Respondents who answered. Required for multi_choice, where `counts` may
   * sum past it (it is the percentage denominator); optional elsewhere,
   * where it equals the sum of `counts`.
   */
  answered?: number
}

export interface NpsAggregate {
  type: 'nps'
  /** All 11 buckets, keys "0".."10". */
  counts_by_score: Record<string, number>
  /** Precomputed round(100 * (promoters - detractors) / total). */
  score: number
}

export interface FreeTextAggregate {
  type: 'free_text'
  answered: number
  snippets: string[]
}

export type QuestionAggregate = DistributionAggregate | NpsAggregate | FreeTextAggregate

export interface CutSegment {
  key: string
  label: string
  n: number
  share: number
  /** Same aggregate shapes as the top level, capped at `n`; no free_text. */
  questions: Record<string, DistributionAggregate>
}

export interface CutAggregates {
  segments: CutSegment[]
}

export interface ExampleTheme {
  label: string
  mentions: number
  quotes: string[]
}

export interface ExampleNarrative {
  headline: string
  key_findings: string[]
  caveats: string[]
}

export interface SampleDataset {
  response_count: number
  questions: Record<string, QuestionAggregate>
  cuts?: Record<string, CutAggregates>
  /** Preview-only stand-in for LLM theme extraction (theme_list blocks). */
  example_themes?: ExampleTheme[]
  /** Preview-only stand-in for the LLM narrative. */
  example_narrative: ExampleNarrative
}

export interface PackFile {
  slug: string
  name: string
  version: number
  focus: PackFocus
  description: string
  headline_questions: string[]
  question_manifest: PackQuestion[]
  insight_spec: InsightSpec
  sample_dataset: SampleDataset
}
