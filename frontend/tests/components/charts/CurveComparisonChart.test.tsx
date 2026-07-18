import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { CurveComparisonChart } from '@/components/charts/CurveComparisonChart'
import { goldCurveSnapshotFixture } from '../../mocks/fixtures/curve'
import type { AssetSnapshotWithLabel } from '@/api/hooks/useCurveSnapshots'

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

const goldSnapshot: AssetSnapshotWithLabel = {
  asset: 'gold',
  label: 'Gold',
  snapshot: { ...goldCurveSnapshotFixture },
}

const wtiSnapshot: AssetSnapshotWithLabel = {
  asset: 'wti',
  label: 'WTI Crude',
  snapshot: {
    ...goldCurveSnapshotFixture,
    asset: 'wti',
    front_price: 78.20,
    points: [
      { ticker: 'CLQ26', close: 78.20, days_to_delivery: 30, data_date: '2026-07-17' },
      { ticker: 'CLU26', close: 79.10, days_to_delivery: 61, data_date: '2026-07-17' },
    ],
  },
}

describe('CurveComparisonChart', () => {
  it('renders ChartFrame without errors with 2-asset fixture', () => {
    expect(() =>
      render(
        <CurveComparisonChart snapshots={[goldSnapshot, wtiSnapshot]} height={320} />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('loading=true → ChartFrame loading state', () => {
    render(
      <CurveComparisonChart snapshots={[]} height={320} loading={true} />,
      { wrapper: Wrapper }
    )
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('empty snapshots → ChartFrame empty state', () => {
    render(
      <CurveComparisonChart
        snapshots={[]}
        height={320}
        empty={{ message: 'Select assets to compare.' }}
      />,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('Select assets to compare.')).toBeInTheDocument()
  })
})
