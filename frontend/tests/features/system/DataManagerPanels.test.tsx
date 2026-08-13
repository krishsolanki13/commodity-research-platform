import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/app/queryClient'
import { DataQCPanel } from '@/features/system/DataQCPanel'
import { COTDataPanel } from '@/features/system/COTDataPanel'
import { EIADataPanel } from '@/features/system/EIADataPanel'

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

vi.mock('@/api/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/hooks')>()
  return {
    ...actual,
    useDataQC: vi.fn(),
    useCOTData: vi.fn(),
    useEIAData: vi.fn(),
  }
})

import { useDataQC, useCOTData, useEIAData } from '@/api/hooks'

describe('DataQCPanel', () => {
  it('shows loading skeleton when isLoading', () => {
    vi.mocked(useDataQC).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useDataQC>)

    const { container } = render(<DataQCPanel asset="gold" />, { wrapper: Wrapper })
    expect(container.querySelector('.animate-pulse')).toBeTruthy()
  })
})

describe('COTDataPanel', () => {
  it('shows EmptyState when available=false', () => {
    vi.mocked(useCOTData).mockReturnValue({
      data: {
        asset: 'brent',
        available: false,
        records: [],
        message: 'COT data is not available for this asset.',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useCOTData>)

    render(<COTDataPanel asset="brent" />, { wrapper: Wrapper })
    expect(screen.getByText('No COT data available')).toBeInTheDocument()
    expect(
      screen.getByText('COT data is not available for this asset.'),
    ).toBeInTheDocument()
  })
})

describe('EIADataPanel', () => {
  it('shows EmptyState when available=false', () => {
    vi.mocked(useEIAData).mockReturnValue({
      data: {
        asset: 'gold',
        available: false,
        records: [],
        message: 'EIA inventory data is not available for this asset.',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useEIAData>)

    render(<EIADataPanel asset="gold" />, { wrapper: Wrapper })
    expect(screen.getByText('No EIA data available')).toBeInTheDocument()
    expect(
      screen.getByText('EIA inventory data is not available for this asset.'),
    ).toBeInTheDocument()
  })
})
