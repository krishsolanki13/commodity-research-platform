import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { CorrelationHeatmapChart } from '@/components/charts/CorrelationHeatmapChart'

const twoAssetMatrix = {
  gold: { gold: 1.0, silver: 0.65 },
  silver: { gold: 0.65, silver: 1.0 },
}

const twoAssets = ['gold', 'silver']

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('CorrelationHeatmapChart', () => {
  it('renders without errors with a 2-asset correlation matrix', () => {
    expect(() =>
      render(
        <CorrelationHeatmapChart
          correlationMatrix={twoAssetMatrix}
          assets={twoAssets}
        />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()
  })

  it('renders the loading state when loading=true', () => {
    render(
      <CorrelationHeatmapChart
        correlationMatrix={twoAssetMatrix}
        assets={twoAssets}
        loading={true}
      />,
      { wrapper: Wrapper }
    )

    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })

  it('renders the empty state without throwing for an empty correlation matrix', () => {
    expect(() =>
      render(
        <CorrelationHeatmapChart correlationMatrix={{}} assets={[]} />,
        { wrapper: Wrapper }
      )
    ).not.toThrow()

    expect(screen.getByText('No correlation data')).toBeInTheDocument()
  })
})
