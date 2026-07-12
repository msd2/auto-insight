import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  type RouterHistory,
} from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/Dashboard'
import { DevPackPreviewPage } from './pages/DevPackPreview'
import { DevPacksPage } from './pages/DevPacks'
import { EventsPage } from './pages/Events'
import { LoginPage } from './pages/Login'
import { ReportsPage } from './pages/Reports'
import { SurveysPage } from './pages/Surveys'

const rootRoute = createRootRoute({
  component: Outlet,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

// Layout route for authenticated pages. Auth guarding lands in WP 0.3.
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'app',
  component: AppShell,
})

const dashboardRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  component: DashboardPage,
})

const eventsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/events',
  component: EventsPage,
})

const surveysRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/surveys',
  component: SurveysPage,
})

const reportsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/reports',
  component: ReportsPage,
})

// Dev-only pack catalogue preview (WP 0.5) — outside the AppShell, not in nav.
const devPacksRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dev/packs',
  component: DevPacksPage,
})

const devPackPreviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dev/packs/$slug',
  component: DevPackPreviewPage,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  devPacksRoute,
  devPackPreviewRoute,
  appRoute.addChildren([dashboardRoute, eventsRoute, surveysRoute, reportsRoute]),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history })
}

export const router = createAppRouter()

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
