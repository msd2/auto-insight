/**
 * Chart palette. Categorical slots are a fixed, CVD-validated order (worst
 * adjacent-pair ΔE 24.2 under protanopia) — always assigned in order, never
 * cycled or re-ranked. Likert scales use a diverging construction (red pole,
 * neutral midpoint, blue pole); NPS bands use the same diverging pair.
 */

/** Fixed-order categorical slots — assign in order, never skip or cycle. */
export const CATEGORICAL = [
  '#2a78d6', // blue
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
  '#e87ba4', // magenta
  '#eb6834', // orange
] as const

/** Single-hue accent for one-series magnitude charts. */
export const ACCENT = '#2a78d6'

/** Diverging steps for a 5-point agree/disagree scale (red → gray → blue). */
export const DIVERGING_5 = ['#d03b3b', '#e9a19f', '#e1e0d9', '#9ec5f4', '#2a78d6'] as const

/** Diverging steps for a 7-point scale. */
export const DIVERGING_7 = [
  '#b02f2f',
  '#d03b3b',
  '#e9a19f',
  '#e1e0d9',
  '#9ec5f4',
  '#2a78d6',
  '#1c5cab',
] as const

/** NPS band colours: detractor / passive / promoter (diverging pair + neutral). */
export const NPS_BANDS = {
  detractor: '#d03b3b',
  passive: '#b9b8b0',
  promoter: '#2a78d6',
} as const

/** Chart chrome. */
export const CHROME = {
  surface: '#ffffff',
  gridline: '#e1e0d9',
  axisLine: '#c3c2b7',
  mutedInk: '#898781',
  secondaryInk: '#52514e',
  primaryInk: '#0b0b0b',
} as const

export function divergingScale(steps: number): readonly string[] {
  return steps === 7 ? DIVERGING_7 : DIVERGING_5
}
