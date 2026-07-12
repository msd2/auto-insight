import { Link, Outlet } from '@tanstack/react-router'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/events', label: 'Events' },
  { to: '/surveys', label: 'Surveys' },
  { to: '/reports', label: 'Reports' },
] as const

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Auto Insight</span>
        {/* Real org name arrives with auth/membership in WP 0.3 */}
        <span className="org-name">Organisation</span>
      </header>
      <div className="app-body">
        <nav className="app-sidebar" aria-label="Primary">
          <ul>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <Link to={item.to} activeProps={{ className: 'active' }}>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
