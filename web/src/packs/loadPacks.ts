import type { PackFile } from './types'

/**
 * Load every pack version file straight from `content/packs/` — the single
 * source of truth — via Vite's eager glob import. Nothing is copied into
 * `web/`; adding a new pack file makes it appear here (and in the per-pack
 * smoke tests) automatically.
 */
const modules = import.meta.glob('../../../content/packs/*/v*.json', {
  eager: true,
  import: 'default',
}) as Record<string, PackFile>

/** Latest version of each pack, sorted by name. */
export const packs: PackFile[] = Object.values(
  Object.values(modules).reduce<Record<string, PackFile>>((latest, pack) => {
    const current = latest[pack.slug]
    if (!current || pack.version > current.version) {
      latest[pack.slug] = pack
    }
    return latest
  }, {}),
).sort((a, b) => a.name.localeCompare(b.name))

export function getPack(slug: string): PackFile | undefined {
  return packs.find((pack) => pack.slug === slug)
}
