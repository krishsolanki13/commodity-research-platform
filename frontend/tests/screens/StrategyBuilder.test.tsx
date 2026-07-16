import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../setup'
import { qk } from '@/api/queryKeys'
import StrategyBuilder from '@/screens/backtest/StrategyBuilder'
import { MOCK_RUN_ID, goldEmaRunDetailFixture } from '../mocks/fixtures/run-detail'

function createTestClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderStrategyBuilder(
  url: string,
  qc = createTestClient(),
  withRunsRoute = false
) {
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/backtest/new" element={<StrategyBuilder />} />
          {withRunsRoute && (
            <Route path="/runs/:runId" element={<div data-testid="run-detail-page" />} />
          )}
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const BASE_URL =
  '/backtest/new?asset=gold&strategy=ema_crossover&params=' +
  encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))

describe('StrategyBuilder', () => {
  it('pre-fills asset and strategy context from URL params', async () => {
    renderStrategyBuilder(BASE_URL)
    await waitFor(() =>
      expect(screen.getAllByText(/gold/i).length).toBeGreaterThan(0)
    )
    expect(screen.getByRole('heading', { name: /strategy builder/i })).toBeInTheDocument()
  })

  it('shows cached signal evaluation when present in TanStack Query cache', async () => {
    const qc = createTestClient()
    const parsedParams = { fast_period: 50, slow_period: 200 }
    qc.setQueryData(qk.signalEvaluate('gold', 'ema_crossover', parsedParams), {
      evaluation: goldEmaRunDetailFixture.signal_evaluation,
    })
    renderStrategyBuilder(BASE_URL, qc)
    await waitFor(() => expect(screen.getByText(/noise/i)).toBeInTheDocument())
  })

  it('?evalOverride=1 shows IC Gate override notice in EvalSummaryCard', async () => {
    const overrideUrl = BASE_URL + '&evalOverride=1'
    renderStrategyBuilder(overrideUrl)
    await waitFor(() => expect(screen.getByText(/ic gate override/i)).toBeInTheDocument())
  })

  it('clicking Launch Backtest triggers the POST /api/backtests mutation', async () => {
    const user = userEvent.setup()
    let postWasCalled = false
    server.use(
      http.post('http://localhost:8000/api/backtests', () => {
        postWasCalled = true
        return HttpResponse.json({ run_id: MOCK_RUN_ID, status: 'queued' }, { status: 202 })
      })
    )
    renderStrategyBuilder(BASE_URL, createTestClient(), false)
    await user.click(screen.getByRole('button', { name: /launch backtest/i }))
    await waitFor(() => expect(postWasCalled).toBe(true))
  })

  it('navigates to /runs/:runId after backtest reaches complete status', async () => {
    const user = userEvent.setup()
    renderStrategyBuilder(BASE_URL, createTestClient(), true)
    await user.click(screen.getByRole('button', { name: /launch backtest/i }))
    await waitFor(() => expect(screen.getByTestId('run-detail-page')).toBeInTheDocument(), {
      timeout: 3000,
    })
  })
})
