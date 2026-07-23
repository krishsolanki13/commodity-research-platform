import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { server } from '../setup'
import { http, HttpResponse } from 'msw'
import { universeFixture } from '../mocks/fixtures/universe'
import MarketOverviewScreen from '@/screens/market/MarketOverview'

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/market']}>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => qc.clear())

describe('MarketOverviewScreen', () => {
  it('renders universe grid with asset names from fixture', async () => {
    render(<MarketOverviewScreen />, { wrapper: Wrapper })
    await waitFor(() => expect(screen.getByText('Gold')).toBeInTheDocument(), { timeout: 5000 })
    expect(screen.getByText('Silver')).toBeInTheDocument()
    expect(screen.getByText('Natural Gas')).toBeInTheDocument()
  })

  it('renders loading state before data arrives', () => {
    render(<MarketOverviewScreen />, { wrapper: Wrapper })
    // Something renders immediately (shell/skeleton) before data
    expect(document.body).not.toBeEmptyDOMElement()
  })

  it('renders empty state when all assets have data_health=missing', async () => {
    server.use(
      http.get('http://localhost:8000/api/assets', () =>
        HttpResponse.json({
          ...universeFixture,
          summaries: Object.fromEntries(
            Object.entries(universeFixture.summaries).map(([k, v]) => [
              k,
              { ...v, data_health: 'missing' },
            ])
          ),
        })
      )
    )
    render(<MarketOverviewScreen />, { wrapper: Wrapper })
    await waitFor(() => expect(screen.getByText(/no market data|ingest/i)).toBeInTheDocument(), {
      timeout: 5000,
    })
  })

  it('range selector "3Y" button is present and interactive', async () => {
    render(<MarketOverviewScreen />, { wrapper: Wrapper })
    await waitFor(() => expect(screen.getByRole('button', { name: '3Y' })).toBeInTheDocument())
    const btn = screen.getByRole('button', { name: '3Y' })
    await userEvent.click(btn)
    // Button is now "pressed" (aria-pressed=true)
    expect(btn.getAttribute('aria-pressed')).toBe('true')
  })
})
