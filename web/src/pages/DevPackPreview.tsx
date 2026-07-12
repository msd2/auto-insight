import { Link, useParams } from '@tanstack/react-router'
import { getPack } from '../packs/loadPacks'
import { PackPreview } from '../packs/PackPreview'

/** Dev-only preview of a single insight pack rendered from its sample data. */
export function DevPackPreviewPage() {
  const { slug } = useParams({ strict: false }) as { slug?: string }
  const pack = slug ? getPack(slug) : undefined
  return (
    <main className="dev-packs-page">
      <p>
        <Link to="/dev/packs">← All packs</Link>
      </p>
      {pack ? <PackPreview pack={pack} /> : <p>No pack found for “{slug}”.</p>}
    </main>
  )
}
