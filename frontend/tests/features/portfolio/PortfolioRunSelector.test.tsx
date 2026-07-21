import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PortfolioRunSelector } from '@/features/portfolio/PortfolioRunSelector'
import { usePortfolioHistory } from '@/stores/portfolioHistory'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={['/portfolio']}>
        <Routes>
          <Route path="/portfolio" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('PortfolioRunSelector', () => {
  beforeEach(() => {
    usePortfolioHistory.setState({ runs: [] })
    localStorage.clear()
  })

  it('renders null when history is empty', () => {
    usePortfolioHistory.setState({ runs: [] })
    const { container } = render(<PortfolioRunSelector />, { wrapper: Wrapper })
    expect(container.firstChild).toBeNull()
  })

  it('renders Select when history has runs', async () => {
    usePortfolioHistory.setState({
      runs: [
        {
          run_id: MOCK_PORTFOLIO_RUN_ID,
          strategy: 'ema_crossover',
          executed_at: '2026-07-19T12:00:00Z',
          n_assets: 6,
          total_return: 0.0125,
        },
      ],
    })

    render(<PortfolioRunSelector />, { wrapper: Wrapper })
    await waitFor(() => screen.getByRole('combobox'))
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })
})
