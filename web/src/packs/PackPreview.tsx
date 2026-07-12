import {
  answeredCount,
  formatMean,
  formatPercent,
  meanScore,
  optionShare,
  topTwoBoxShare,
} from './aggregates'
import {
  CutMeanBarChart,
  CutStackedChart,
  DistributionColumnChart,
  LikertStackedChart,
  MeanBarChart,
  MetricTile,
  NpsChart,
  OptionShareChart,
  QuoteListBlock,
  ThemeListBlock,
} from './charts'
import type {
  DistributionAggregate,
  FreeTextAggregate,
  InsightBlock,
  NpsAggregate,
  PackFile,
  PackQuestion,
  QuestionAggregate,
} from './types'

/**
 * Renders one pack entirely from its version file: metadata, every
 * insight-spec block from the sample dataset (the canonical aggregate
 * shapes), and the example narrative. Purely data-driven — this is the seed
 * of the WP 2.1 catalogue preview.
 */

function question(pack: PackFile, id: string): PackQuestion {
  const found = pack.question_manifest.find((q) => q.id === id)
  if (!found) throw new Error(`Unknown question id: ${id}`)
  return found
}

function questionLabel(q: PackQuestion): string {
  if (q.dimension) return q.dimension.charAt(0).toUpperCase() + q.dimension.slice(1)
  return q.prompt
}

function aggregate(pack: PackFile, id: string): QuestionAggregate {
  const agg = pack.sample_dataset.questions[id]
  if (!agg) throw new Error(`No sample aggregate for question: ${id}`)
  return agg
}

function asDistribution(agg: QuestionAggregate, id: string): DistributionAggregate {
  if (agg.type !== 'distribution') throw new Error(`Expected distribution aggregate for ${id}`)
  return agg
}

function asNps(agg: QuestionAggregate, id: string): NpsAggregate {
  if (agg.type !== 'nps') throw new Error(`Expected nps aggregate for ${id}`)
  return agg
}

function asFreeText(agg: QuestionAggregate, id: string): FreeTextAggregate {
  if (agg.type !== 'free_text') throw new Error(`Expected free_text aggregate for ${id}`)
  return agg
}

const CHOICE_TYPES = new Set(['single_choice', 'multi_choice', 'demographic'])

function MetricTileBlock({ pack, block }: { pack: PackFile; block: InsightBlock }) {
  const q = question(pack, block.question_ids[0])
  const agg = aggregate(pack, q.id)
  switch (block.measure) {
    case 'nps': {
      const nps = asNps(agg, q.id)
      return (
        <MetricTile
          label={block.title}
          value={nps.score >= 0 ? `+${nps.score}` : String(nps.score)}
          detail={`Net Promoter Score · ${pack.sample_dataset.response_count} responses`}
        />
      )
    }
    case 'mean': {
      const dist = asDistribution(agg, q.id)
      return (
        <MetricTile
          label={block.title}
          value={`${formatMean(meanScore(dist))} / ${dist.labels.length}`}
          detail={`Mean rating · ${answeredCount(dist)} responses`}
        />
      )
    }
    case 'top_two_box_share': {
      const dist = asDistribution(agg, q.id)
      return (
        <MetricTile
          label={block.title}
          value={formatPercent(topTwoBoxShare(dist))}
          detail={`Agree or strongly agree · ${answeredCount(dist)} responses`}
        />
      )
    }
    case 'option_share': {
      const dist = asDistribution(agg, q.id)
      const optionLabel = block.option_label ?? ''
      return (
        <MetricTile
          label={block.title}
          value={formatPercent(optionShare(dist, optionLabel))}
          detail={`Answered “${optionLabel}” · ${answeredCount(dist)} responses`}
        />
      )
    }
    default:
      throw new Error(`Unknown metric measure on block ${block.id}`)
  }
}

function CutBarBlock({ pack, block }: { pack: PackFile; block: InsightBlock }) {
  const cut = pack.sample_dataset.cuts?.[block.cut ?? '']
  if (!cut) throw new Error(`Missing cut data for block ${block.id}`)
  const rows = block.question_ids.map((id) => {
    const q = question(pack, id)
    const means: Record<string, number> = {}
    for (const segment of cut.segments) {
      const agg = segment.questions[id]
      if (!agg) throw new Error(`Missing segment aggregate for ${id}`)
      means[segment.label] = meanScore(agg)
    }
    return { label: questionLabel(q), means }
  })
  return <CutMeanBarChart rows={rows} segmentLabels={cut.segments.map((s) => s.label)} />
}

function CutStackedBlock({ pack, block }: { pack: PackFile; block: InsightBlock }) {
  const cut = pack.sample_dataset.cuts?.[block.cut ?? '']
  if (!cut) throw new Error(`Missing cut data for block ${block.id}`)
  const id = block.question_ids[0]
  const optionLabels = asDistribution(aggregate(pack, id), id).labels
  const rows = cut.segments.map((segment) => {
    const agg = segment.questions[id]
    if (!agg) throw new Error(`Missing segment aggregate for ${id}`)
    const denominator = answeredCount(agg)
    const shares: Record<string, number> = {}
    agg.labels.forEach((label, i) => {
      shares[label] = denominator === 0 ? 0 : (100 * agg.counts[i]) / denominator
    })
    return { label: `${segment.label} (n=${segment.n})`, shares }
  })
  return <CutStackedChart rows={rows} optionLabels={optionLabels} />
}

function BlockContent({ pack, block }: { pack: PackFile; block: InsightBlock }) {
  switch (block.kind) {
    case 'metric_tile':
      return <MetricTileBlock pack={pack} block={block} />
    case 'bar': {
      if (block.cut && block.cut !== 'none') return <CutBarBlock pack={pack} block={block} />
      const first = question(pack, block.question_ids[0])
      if (block.question_ids.length === 1 && CHOICE_TYPES.has(first.type)) {
        return (
          <OptionShareChart
            aggregate={asDistribution(aggregate(pack, first.id), first.id)}
            multiChoice={first.type === 'multi_choice'}
          />
        )
      }
      const rows = block.question_ids.map((id) => ({
        label: questionLabel(question(pack, id)),
        aggregate: asDistribution(aggregate(pack, id), id),
      }))
      return <MeanBarChart rows={rows} />
    }
    case 'stacked_bar': {
      if (block.cut && block.cut !== 'none') return <CutStackedBlock pack={pack} block={block} />
      const rows = block.question_ids.map((id) => ({
        label: questionLabel(question(pack, id)),
        aggregate: asDistribution(aggregate(pack, id), id),
      }))
      return <LikertStackedChart rows={rows} />
    }
    case 'distribution': {
      const id = block.question_ids[0]
      const agg = aggregate(pack, id)
      if (agg.type === 'nps') return <NpsChart aggregate={asNps(agg, id)} />
      return <DistributionColumnChart aggregate={asDistribution(agg, id)} />
    }
    case 'theme_list':
      return <ThemeListBlock themes={pack.sample_dataset.example_themes ?? []} />
    case 'quote_list': {
      const items = block.question_ids.map((id) => ({
        prompt: question(pack, id).prompt,
        aggregate: asFreeText(aggregate(pack, id), id),
      }))
      return <QuoteListBlock items={items} />
    }
    case 'line':
      return <p className="pack-chart-note">Time-series block — no sample data yet.</p>
    default:
      throw new Error(`Unknown block kind on block ${block.id}`)
  }
}

export function PackPreview({ pack }: { pack: PackFile }) {
  const narrative = pack.sample_dataset.example_narrative
  return (
    <article className="pack-preview">
      <header className="pack-header">
        <h2>
          {pack.name} <span className={`pack-focus pack-focus-${pack.focus}`}>{pack.focus}</span>
        </h2>
        <p className="pack-description">{pack.description}</p>
        <ul className="pack-headline-questions">
          {pack.headline_questions.map((hq) => (
            <li key={hq}>{hq}</li>
          ))}
        </ul>
        <p className="pack-chart-note">
          v{pack.version} · {pack.question_manifest.length} questions · sample dataset of{' '}
          {pack.sample_dataset.response_count} responses (illustrative preview data)
        </p>
      </header>
      {pack.insight_spec.blocks.map((block) => (
        <section key={block.id} className="pack-block">
          <h3>{block.title}</h3>
          <BlockContent pack={pack} block={block} />
        </section>
      ))}
      <section className="pack-block pack-narrative">
        <h3>Example report narrative</h3>
        <p className="pack-narrative-headline">{narrative.headline}</p>
        <h4>Key findings</h4>
        <ul>
          {narrative.key_findings.map((finding) => (
            <li key={finding}>{finding}</li>
          ))}
        </ul>
        <h4>Caveats</h4>
        <ul className="pack-caveats">
          {narrative.caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      </section>
    </article>
  )
}
