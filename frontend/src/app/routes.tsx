import React, { Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/app/shell/AppShell'
import { RouteErrorBoundary } from '@/components/layout/RouteErrorBoundary'

function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center font-mono text-sm text-text-secondary">
      Loading...
    </div>
  )
}

function wrap(el: React.ReactElement) {
  return <Suspense fallback={<PageLoader />}>{el}</Suspense>
}

function route(el: React.ReactElement) {
  return { element: wrap(el), errorElement: <RouteErrorBoundary /> }
}

const MarketOverview = React.lazy(() => import('@/screens/market/MarketOverview'))
const AssetDetail = React.lazy(() => import('@/screens/market/AssetDetail'))
const ResearchWorkbench = React.lazy(() => import('@/screens/research/ResearchWorkbench'))
const StrategyBuilder = React.lazy(() => import('@/screens/backtest/StrategyBuilder'))
const RunExplorer = React.lazy(() => import('@/screens/runs/RunExplorer'))
const RunComparison = React.lazy(() => import('@/screens/runs/RunComparison'))
const SweepExplorer = React.lazy(() =>
  import('@/screens/sweeps/SweepExplorer').then((m) => ({ default: m.SweepExplorer }))
)
const RunDetail = React.lazy(() => import('@/screens/runs/RunDetail'))
const PortfolioAnalytics = React.lazy(() => import('@/screens/portfolio/PortfolioAnalytics'))
const FuturesCurve = React.lazy(() => import('@/screens/intelligence/FuturesCurve'))
const CurvePCA = React.lazy(() =>
  import('@/screens/intelligence/CurvePCA').then((m) => ({ default: m.CurvePCA }))
)
const CurveComparison = React.lazy(() =>
  import('@/screens/intelligence/CurveComparison').then((module) => ({
    default: module.CurveComparison,
  }))
)
const DataManager = React.lazy(() => import('@/screens/system/DataManager'))
const Configuration = React.lazy(() => import('@/screens/system/Configuration'))
const NotFound = React.lazy(() => import('@/screens/NotFound'))
const Gallery = React.lazy(() => import('@/screens/dev/Gallery'))

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    errorElement: <RouteErrorBoundary />,
    children: [
      { path: '/', element: <Navigate to="/market" replace /> },
      { path: '/market', ...route(<MarketOverview />) },
      { path: '/market/:asset', ...route(<AssetDetail />) },
      { path: '/research', ...route(<ResearchWorkbench />) },
      { path: '/backtest/new', ...route(<StrategyBuilder />) },
      { path: '/runs', ...route(<RunExplorer />) },
      { path: '/runs/compare', ...route(<RunComparison />) },
      { path: '/sweeps', ...route(<SweepExplorer />) },
      { path: '/runs/:runId', ...route(<RunDetail />) },
      { path: '/portfolio', ...route(<PortfolioAnalytics />) },
      { path: '/intelligence', ...route(<FuturesCurve />) },
      { path: '/intelligence/pca', ...route(<CurvePCA />) },
      { path: '/intelligence/compare', ...route(<CurveComparison />) },
      { path: '/system/data', ...route(<DataManager />) },
      { path: '/system/config', ...route(<Configuration />) },
      { path: '*', ...route(<NotFound />) },
    ],
  },
  // Gallery is outside AppShell — no TopBar/sidebar on this route
  { path: '/dev/gallery', ...route(<Gallery />) },
])
