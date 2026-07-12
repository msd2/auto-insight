import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { createAppRouter } from '../router'
import { packs } from './loadPacks'
import { PackPreview } from './PackPreview'

afterEach(cleanup)

describe('pack catalogue preview', () => {
  it('loads every pack from content/packs via the glob import', () => {
    expect(packs.length).toBeGreaterThan(0)
    for (const pack of packs) {
      expect(pack.slug).toBeTruthy()
      expect(pack.sample_dataset.response_count).toBeGreaterThan(0)
    }
  })

  it('lists every pack on the /dev/packs catalogue route', async () => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: ['/dev/packs'] }))
    render(<RouterProvider router={router} />)
    await screen.findByRole('heading', { name: 'Insight pack catalogue preview' })
    for (const pack of packs) {
      expect(screen.getByRole('link', { name: pack.name })).toBeInTheDocument()
    }
  })

  // One smoke test per pack file, driven by the same glob import — a new
  // pack in content/packs/ is covered automatically.
  describe.each(packs.map((pack) => [pack.slug, pack] as const))('%s', (_slug, pack) => {
    it('renders every insight block from sample data without throwing', () => {
      const { container } = render(<PackPreview pack={pack} />)
      expect(screen.getByRole('heading', { name: new RegExp(pack.name) })).toBeInTheDocument()
      expect(container.querySelectorAll('.pack-chart').length).toBeGreaterThan(0)
      // Every block title is rendered.
      for (const block of pack.insight_spec.blocks) {
        expect(screen.getByRole('heading', { name: block.title })).toBeInTheDocument()
      }
      // The example narrative is rendered as the example-report text.
      expect(screen.getByText(pack.sample_dataset.example_narrative.headline)).toBeInTheDocument()
    })

    it('is reachable at /dev/packs/$slug', async () => {
      const router = createAppRouter(
        createMemoryHistory({ initialEntries: [`/dev/packs/${pack.slug}`] }),
      )
      render(<RouterProvider router={router} />)
      expect(
        await screen.findByRole('heading', { name: new RegExp(pack.name) }),
      ).toBeInTheDocument()
    })
  })
})
