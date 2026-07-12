import { Link } from '@tanstack/react-router'
import { packs } from '../packs/loadPacks'

/**
 * Dev-only catalogue preview (WP 0.5): lists every insight pack loaded
 * straight from `content/packs/`. Not linked from the AppShell nav.
 */
export function DevPacksPage() {
  return (
    <main className="dev-packs-page">
      <h1>Insight pack catalogue preview</h1>
      <p className="pack-chart-note">
        Dev page — renders each pack from its version file in <code>content/packs/</code>. Question
        wording is draft; sample data is illustrative.
      </p>
      <ul className="dev-pack-list">
        {packs.map((pack) => (
          <li key={pack.slug} className="dev-pack-card">
            <h2>
              <Link to="/dev/packs/$slug" params={{ slug: pack.slug }}>
                {pack.name}
              </Link>{' '}
              <span className={`pack-focus pack-focus-${pack.focus}`}>{pack.focus}</span>
            </h2>
            <p>{pack.description}</p>
            <ul className="pack-headline-questions">
              {pack.headline_questions.map((hq) => (
                <li key={hq}>{hq}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </main>
  )
}
