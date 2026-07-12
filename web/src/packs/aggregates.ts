import type { DistributionAggregate, NpsAggregate } from './types'

/**
 * Pure helpers over the canonical aggregate shapes (`content/README.md`).
 * Shared by the preview charts and reusable against real WP 5.1 aggregates.
 */

export function totalCount(agg: DistributionAggregate): number {
  return agg.counts.reduce((sum, count) => sum + count, 0)
}

/**
 * Percentage denominator for a distribution: `answered` when present
 * (required for multi_choice, where counts sum past it), else the sum of
 * counts (single-select).
 */
export function answeredCount(agg: DistributionAggregate): number {
  return agg.answered ?? totalCount(agg)
}

/** Mean scale point of a likert distribution (scale points 1..k). */
export function meanScore(agg: DistributionAggregate): number {
  const total = totalCount(agg)
  if (total === 0) return 0
  const weighted = agg.counts.reduce((sum, count, i) => sum + count * (i + 1), 0)
  return weighted / total
}

/** Share answering the top two scale points of a likert distribution. */
export function topTwoBoxShare(agg: DistributionAggregate): number {
  const total = totalCount(agg)
  if (total === 0) return 0
  const k = agg.counts.length
  return (agg.counts[k - 1] + agg.counts[k - 2]) / total
}

/** Share choosing a given option (multi-choice uses `answered` as denominator). */
export function optionShare(agg: DistributionAggregate, optionLabel: string): number {
  const denominator = answeredCount(agg)
  if (denominator === 0) return 0
  const index = agg.labels.indexOf(optionLabel)
  return index === -1 ? 0 : agg.counts[index] / denominator
}

export interface NpsBands {
  detractors: number
  passives: number
  promoters: number
  total: number
}

/** Detractor (0-6) / passive (7-8) / promoter (9-10) counts. */
export function npsBands(agg: NpsAggregate): NpsBands {
  const bands: NpsBands = { detractors: 0, passives: 0, promoters: 0, total: 0 }
  for (let score = 0; score <= 10; score += 1) {
    const count = agg.counts_by_score[String(score)] ?? 0
    bands.total += count
    if (score <= 6) bands.detractors += count
    else if (score <= 8) bands.passives += count
    else bands.promoters += count
  }
  return bands
}

export function formatPercent(share: number): string {
  return `${Math.round(share * 100)}%`
}

export function formatMean(value: number): string {
  return value.toFixed(2)
}
