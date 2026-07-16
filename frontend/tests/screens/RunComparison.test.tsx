import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { RunComparison } from '@/screens/runs/RunComparison'
import { MOCK_RUN_ID } from '../mocks/fixtures/run-detail'
import { MOCK_RUN_ID_2 } from '../mocks/fixtures/run-list'

const COMPARE_URL = `/runs/compare?ids=${MOCK_RUN_ID},${MOCK_RUN_ID_2}`

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ url = COMPARE_URL }: { url?: string }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/runs" element={<div data-testid="run-explorer" />} />
          <Route path="/runs/:runId" element={<div data-testid="run-detail" />} />
          <Route path="/runs/compare" element={<RunComparison />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RunComparison', () => {
  beforeEach(() => {
    qc.clear()
  })

  it('renders AlignedCurvesChart title and MetricDeltaTable metrics with compare fixture', async () => {
    render(<Wrapper />)
    await waitFor(() =>
      expect(screen.getByText('Normalized Returns')).toBeInTheDocument()
    )
    await waitFor(() =>
      expect(screen.getByText('Sharpe')).toBeInTheDocument()
    )
  })

  it('single ID in URL redirects to run detail page', async () => {
    render(<Wrapper url={`/runs/compare?ids=${MOCK_RUN_ID}`} />)
    await waitFor(() =>
      expect(screen.getByTestId('run-detail')).toBeInTheDocument()
    )
  })

  it('zero IDs in URL redirects to run explorer', async () => {
    render(<Wrapper url="/runs/compare" />)
    await waitFor(() =>
      expect(screen.getByTestId('run-explorer')).toBeInTheDocument()
    )
  })

  it('mixed_assets=true shows cross-asset notice', async () => {
    // compareFixture has mixed_assets: true
    render(<Wrapper />)
    await waitFor(() =>
      expect(screen.getByText(/different assets/i)).toBeInTheDocument()
    )
  })

  it('removing a run chip leaves one ID and triggers redirect to run detail', async () => {
    render(<Wrapper />)
    await waitFor(() =>
      expect(screen.getByText('Normalized Returns')).toBeInTheDocument()
    )
    const removeButtons = screen.getAllByRole('button', { name: /remove/i })
    await userEvent.click(removeButtons[0])
    await waitFor(() =>
      expect(screen.getByTestId('run-detail')).toBeInTheDocument()
    )
  })
})
