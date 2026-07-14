import React, { Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/app/shell/AppShell'

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

const MarketOverview = React.lazy(() => import('@/screens/market/MarketOverview'))
const AssetDetail = React.lazy(() => import('@/screens/market/AssetDetail'))
const ResearchWorkbench = React.lazy(() => import('@/screens/research/ResearchWorkbench'))
const StrategyBuilder = React.lazy(() => import('@/screens/backtest/StrategyBuilder'))
const RunExplorer = React.lazy(() => import('@/screens/runs/RunExplorer'))
const RunComparison = React.lazy(() => import('@/screens/runs/RunComparison'))
const RunDetail = React.lazy(() => import('@/screens/runs/RunDetail'))
const DataManager = React.lazy(() => import('@/screens/system/DataManager'))
const Configuration = React.lazy(() => import('@/screens/system/Configuration'))
const NotFound = React.lazy(() => import('@/screens/NotFound'))
const Gallery = React.lazy(() => import('@/screens/dev/Gallery'))

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <Navigate to="/market" replace /> },
      { path: '/market', element: wrap(<MarketOverview />) },
      { path: '/market/:asset', element: wrap(<AssetDetail />) },
      { path: '/research', element: wrap(<ResearchWorkbench />) },
      { path: '/backtest/new', element: wrap(<StrategyBuilder />) },
      { path: '/runs', element: wrap(<RunExplorer />) },
      { path: '/runs/compare', element: wrap(<RunComparison />) },
      { path: '/runs/:runId', element: wrap(<RunDetail />) },
      { path: '/system/data', element: wrap(<DataManager />) },
      { path: '/system/config', element: wrap(<Configuration />) },
      { path: '*', element: wrap(<NotFound />) },
    ],
  },
  // Gallery is outside AppShell — no TopBar/sidebar on this route
  { path: '/dev/gallery', element: wrap(<Gallery />) },
])
