import React, { Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

function PageLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-bg-app text-text-secondary text-sm font-mono">
      Loading...
    </div>
  )
}

const MarketOverview    = React.lazy(() => import('@/screens/market/MarketOverview'))
const AssetDetail       = React.lazy(() => import('@/screens/market/AssetDetail'))
const ResearchWorkbench = React.lazy(() => import('@/screens/research/ResearchWorkbench'))
const StrategyBuilder   = React.lazy(() => import('@/screens/backtest/StrategyBuilder'))
const RunExplorer       = React.lazy(() => import('@/screens/runs/RunExplorer'))
const RunComparison     = React.lazy(() => import('@/screens/runs/RunComparison'))
const RunDetail         = React.lazy(() => import('@/screens/runs/RunDetail'))
const DataManager       = React.lazy(() => import('@/screens/system/DataManager'))
const Configuration     = React.lazy(() => import('@/screens/system/Configuration'))
const NotFound          = React.lazy(() => import('@/screens/NotFound'))

function wrap(element: React.ReactElement) {
  return <Suspense fallback={<PageLoader />}>{element}</Suspense>
}

export const router = createBrowserRouter([
  { path: '/',                element: <Navigate to="/market" replace /> },
  { path: '/market',          element: wrap(<MarketOverview />) },
  { path: '/market/:asset',   element: wrap(<AssetDetail />) },
  { path: '/research',        element: wrap(<ResearchWorkbench />) },
  { path: '/backtest/new',    element: wrap(<StrategyBuilder />) },
  { path: '/runs',            element: wrap(<RunExplorer />) },
  { path: '/runs/compare',    element: wrap(<RunComparison />) },
  { path: '/runs/:runId',     element: wrap(<RunDetail />) },
  { path: '/system/data',     element: wrap(<DataManager />) },
  { path: '/system/config',   element: wrap(<Configuration />) },
  { path: '*',                element: wrap(<NotFound />) },
])
