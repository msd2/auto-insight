import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createAppRouter } from '../router'

describe('AppShell', () => {
  it('renders the sidebar navigation and org placeholder', async () => {
    const router = createAppRouter(createMemoryHistory({ initialEntries: ['/'] }))
    render(<RouterProvider router={router} />)

    expect(await screen.findByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Events' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Surveys' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.getByText('Organisation')).toBeInTheDocument()
  })
})
