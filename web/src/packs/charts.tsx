import type { ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  answeredCount,
  formatMean,
  formatPercent,
  meanScore,
  npsBands,
  totalCount,
} from './aggregates'
import { ACCENT, CATEGORICAL, CHROME, divergingScale, NPS_BANDS } from './palette'
import type { DistributionAggregate, ExampleTheme, FreeTextAggregate, NpsAggregate } from './types'

/**
 * Chart components over the canonical aggregate shapes (`content/README.md`).
 * They are data-driven — no pack-specific branching — so the same components
 * render the WP 2.1 catalogue preview and, later, real WP 5.1 aggregates.
 */

const CHART_WIDTH = 680
const AXIS_TICK = { fill: CHROME.mutedInk, fontSize: 12 } as const
const AXIS_LINE = { stroke: CHROME.axisLine } as const
const TOOLTIP_STYLE = {
  fontSize: 12,
  border: `1px solid ${CHROME.gridline}`,
  borderRadius: 4,
} as const

function ChartFrame({ children }: { children: ReactNode }) {
  return <div className="pack-chart">{children}</div>
}

function legendText(value: string) {
  return <span style={{ color: CHROME.secondaryInk, fontSize: 12 }}>{value}</span>
}

function truncate(label: string, max = 34): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label
}

/** Ink colour for a label sitting inside a coloured fill. */
function inkFor(fillHex: string): string {
  const r = parseInt(fillHex.slice(1, 3), 16) / 255
  const g = parseInt(fillHex.slice(3, 5), 16) / 255
  const b = parseInt(fillHex.slice(5, 7), 16) / 255
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance < 0.55 ? '#ffffff' : CHROME.primaryInk
}

/** Inline percentage label for stacked segments — rendered only where it fits. */
function segmentLabel(fill: string) {
  return function SegmentLabel(props: unknown) {
    const { x, y, width, height, value } = props as {
      x?: number
      y?: number
      width?: number
      height?: number
      value?: number
    }
    if (x == null || y == null || width == null || height == null || value == null) return null
    if (width < 40) return null
    return (
      <text
        x={x + width / 2}
        y={y + height / 2}
        dy={4}
        textAnchor="middle"
        fontSize={11}
        fill={inkFor(fill)}
      >
        {Math.round(value)}%
      </text>
    )
  }
}

/* ---------------------------------------------------------------- tiles */

export function MetricTile({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail: string
}) {
  return (
    <div className="pack-chart pack-metric-tile">
      <div className="pack-metric-label">{label}</div>
      <div className="pack-metric-value">{value}</div>
      <div className="pack-metric-detail">{detail}</div>
    </div>
  )
}

/* ----------------------------------------------------- option share bars */

/**
 * One horizontal bar per option, as a share of respondents. For multi-choice
 * the denominator is `answered` (shares may sum past 100%); for single-select
 * it is the count sum.
 */
export function OptionShareChart({
  aggregate,
  multiChoice = false,
}: {
  aggregate: DistributionAggregate
  multiChoice?: boolean
}) {
  const denominator = answeredCount(aggregate)
  const data = aggregate.labels.map((label, i) => ({
    label,
    count: aggregate.counts[i],
    share: denominator === 0 ? 0 : (100 * aggregate.counts[i]) / denominator,
  }))
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={data.length * 36 + 48}
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
      >
        <CartesianGrid horizontal={false} stroke={CHROME.gridline} />
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          tickFormatter={(v: string) => truncate(v)}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number, _name, item) =>
            [
              `${(item.payload as { count: number }).count} of ${denominator} (${Math.round(value)}%)`,
              'Share',
            ] as [string, string]
          }
        />
        <Bar dataKey="share" fill={ACCENT} barSize={18} radius={[0, 4, 4, 0]} />
      </BarChart>
      {multiChoice && (
        <p className="pack-chart-note">
          Multi-select: shares use the {denominator} respondents who answered and may sum past 100%.
        </p>
      )}
    </ChartFrame>
  )
}

/* ------------------------------------------------------------ histograms */

/** Single-question histogram: one column per option / scale point (counts). */
export function DistributionColumnChart({ aggregate }: { aggregate: DistributionAggregate }) {
  const data = aggregate.labels.map((label, i) => ({ label, count: aggregate.counts[i] }))
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={240}
        data={data}
        margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
      >
        <CartesianGrid vertical={false} stroke={CHROME.gridline} />
        <XAxis
          dataKey="label"
          interval={0}
          tickFormatter={(v: string) => truncate(v, 14)}
          tick={{ ...AXIS_TICK, fontSize: 11 }}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${value} responses`, 'Count'] as [string, string]}
        />
        <Bar dataKey="count" fill={ACCENT} barSize={24} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartFrame>
  )
}

/** Full 0–10 NPS histogram with detractor / passive / promoter bands. */
export function NpsChart({ aggregate }: { aggregate: NpsAggregate }) {
  const bands = npsBands(aggregate)
  const data = Array.from({ length: 11 }, (_, score) => ({
    score: String(score),
    count: aggregate.counts_by_score[String(score)] ?? 0,
    band: score <= 6 ? 'detractor' : score <= 8 ? 'passive' : 'promoter',
  }))
  const legendPayload = [
    { value: 'Detractors (0–6)', color: NPS_BANDS.detractor, type: 'square' as const },
    { value: 'Passives (7–8)', color: NPS_BANDS.passive, type: 'square' as const },
    { value: 'Promoters (9–10)', color: NPS_BANDS.promoter, type: 'square' as const },
  ]
  return (
    <ChartFrame>
      <p className="pack-chart-note">
        NPS {aggregate.score >= 0 ? `+${aggregate.score}` : aggregate.score} ·{' '}
        {formatPercent(bands.detractors / bands.total)} detractors,{' '}
        {formatPercent(bands.passives / bands.total)} passives,{' '}
        {formatPercent(bands.promoters / bands.total)} promoters
      </p>
      <BarChart
        width={CHART_WIDTH}
        height={240}
        data={data}
        margin={{ top: 8, right: 16, bottom: 4, left: 0 }}
      >
        <CartesianGrid vertical={false} stroke={CHROME.gridline} />
        <XAxis dataKey="score" tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} />
        <YAxis tick={AXIS_TICK} axisLine={AXIS_LINE} tickLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${value} responses`, 'Count'] as [string, string]}
        />
        <Legend payload={legendPayload} formatter={legendText} iconSize={10} />
        <Bar dataKey="count" barSize={24} radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.score} fill={NPS_BANDS[entry.band as keyof typeof NPS_BANDS]} />
          ))}
        </Bar>
      </BarChart>
    </ChartFrame>
  )
}

/* ------------------------------------------------------------- mean bars */

export interface MeanBarRow {
  label: string
  aggregate: DistributionAggregate
}

/** One horizontal bar per question: mean scale point (likert summary). */
export function MeanBarChart({ rows }: { rows: MeanBarRow[] }) {
  const scaleMax = Math.max(...rows.map((row) => row.aggregate.labels.length))
  const data = rows.map((row) => ({ label: row.label, mean: meanScore(row.aggregate) }))
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={data.length * 36 + 48}
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 40, bottom: 4, left: 8 }}
      >
        <CartesianGrid horizontal={false} stroke={CHROME.gridline} />
        <XAxis
          type="number"
          domain={[0, scaleMax]}
          tickCount={scaleMax + 1}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          tickFormatter={(v: string) => truncate(v)}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) =>
            [`${formatMean(value)} / ${scaleMax}`, 'Mean'] as [string, string]
          }
        />
        <Bar dataKey="mean" fill={ACCENT} barSize={18} radius={[0, 4, 4, 0]}>
          <LabelList
            dataKey="mean"
            position="right"
            formatter={(value: number) => formatMean(value)}
            style={{ fill: CHROME.secondaryInk, fontSize: 11 }}
          />
        </Bar>
      </BarChart>
    </ChartFrame>
  )
}

/**
 * Grouped mean bars for a box-office cut: one category row per question,
 * one bar per segment. Segment colours follow the fixed categorical order.
 */
export function CutMeanBarChart({
  rows,
  segmentLabels,
}: {
  rows: { label: string; means: Record<string, number> }[]
  segmentLabels: string[]
}) {
  const scaleMax = 5
  const data = rows.map((row) => ({ label: row.label, ...row.means }))
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={data.length * (segmentLabels.length * 22 + 16) + 72}
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 40, bottom: 4, left: 8 }}
      >
        <CartesianGrid horizontal={false} stroke={CHROME.gridline} />
        <XAxis
          type="number"
          domain={[0, scaleMax]}
          tickCount={scaleMax + 1}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          tickFormatter={(v: string) => truncate(v)}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) =>
            [`${formatMean(value)} / ${scaleMax}`, undefined] as [string, undefined]
          }
        />
        <Legend formatter={legendText} iconSize={10} />
        {segmentLabels.map((segment, i) => (
          <Bar
            key={segment}
            dataKey={segment}
            fill={CATEGORICAL[i % CATEGORICAL.length]}
            barSize={16}
            radius={[0, 4, 4, 0]}
          />
        ))}
      </BarChart>
    </ChartFrame>
  )
}

/* ---------------------------------------------------------- stacked bars */

/**
 * 100%-stacked agreement rows (one per likert question), diverging colours
 * centred on the neutral midpoint. Segment labels render where they fit.
 */
export function LikertStackedChart({ rows }: { rows: MeanBarRow[] }) {
  const scaleLabels = rows[0].aggregate.labels
  const colors = divergingScale(scaleLabels.length)
  const data = rows.map((row) => {
    const total = totalCount(row.aggregate)
    const shares: Record<string, number> = {}
    row.aggregate.labels.forEach((label, i) => {
      shares[label] = total === 0 ? 0 : (100 * row.aggregate.counts[i]) / total
    })
    return { label: row.label, ...shares }
  })
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={data.length * 34 + 96}
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
      >
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          tickFormatter={(v: string) => truncate(v)}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${Math.round(value)}%`, undefined] as [string, undefined]}
        />
        <Legend formatter={legendText} iconSize={10} />
        {scaleLabels.map((label, i) => (
          <Bar
            key={label}
            dataKey={label}
            stackId="scale"
            fill={colors[i]}
            barSize={20}
            stroke={CHROME.surface}
            strokeWidth={1}
          >
            <LabelList dataKey={label} content={segmentLabel(colors[i])} />
          </Bar>
        ))}
      </BarChart>
    </ChartFrame>
  )
}

/**
 * Stacked option shares per cut segment (e.g. marketing channel mix per
 * booking-lead-time band). Option colours follow the fixed categorical order.
 */
export function CutStackedChart({
  rows,
  optionLabels,
}: {
  rows: { label: string; shares: Record<string, number> }[]
  optionLabels: string[]
}) {
  const data = rows.map((row) => ({ label: row.label, ...row.shares }))
  return (
    <ChartFrame>
      <BarChart
        width={CHART_WIDTH}
        height={data.length * 40 + 110}
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
      >
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={210}
          tickFormatter={(v: string) => truncate(v)}
          tick={AXIS_TICK}
          axisLine={AXIS_LINE}
          tickLine={false}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value: number) => [`${Math.round(value)}%`, undefined] as [string, undefined]}
        />
        <Legend formatter={legendText} iconSize={10} />
        {optionLabels.map((label, i) => (
          <Bar
            key={label}
            dataKey={label}
            stackId="options"
            fill={CATEGORICAL[i % CATEGORICAL.length]}
            barSize={22}
            stroke={CHROME.surface}
            strokeWidth={1}
          >
            <LabelList
              dataKey={label}
              content={segmentLabel(CATEGORICAL[i % CATEGORICAL.length])}
            />
          </Bar>
        ))}
      </BarChart>
    </ChartFrame>
  )
}

/* ------------------------------------------------------------ text blocks */

export function QuoteListBlock({
  items,
}: {
  items: { prompt: string; aggregate: FreeTextAggregate }[]
}) {
  return (
    <div className="pack-chart pack-quote-list">
      {items.map((item) => (
        <div key={item.prompt}>
          <p className="pack-chart-note">
            “{item.prompt}” — {item.aggregate.answered} answered
          </p>
          <ul>
            {item.aggregate.snippets.map((snippet) => (
              <li key={snippet}>
                <blockquote>{snippet}</blockquote>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

export function ThemeListBlock({ themes }: { themes: ExampleTheme[] }) {
  return (
    <div className="pack-chart pack-theme-list">
      <ol>
        {themes.map((theme) => (
          <li key={theme.label}>
            <div className="pack-theme-head">
              <span className="pack-theme-label">{theme.label}</span>
              <span className="pack-theme-mentions">{theme.mentions} mentions</span>
            </div>
            {theme.quotes.map((quote) => (
              <blockquote key={quote}>{quote}</blockquote>
            ))}
          </li>
        ))}
      </ol>
    </div>
  )
}
