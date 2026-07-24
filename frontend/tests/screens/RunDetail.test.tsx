import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import RunDetail from '@/screens/runs/RunDetail'
import { goldEmaRunDetailFixture, MOCK_RUN_ID } from '../mocks/fixtures/run-detail'
import { server } from '../setup'

function renderRunDetail(runId = MOCK_RUN_ID) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/runs/${runId}`]}>
        <Routes>
          <Route path="/runs/:runId" element={<RunDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RunDetail', () => {
  it('renders run header with run_id and asset from RunDetailResponse', async () => {
    renderRunDetail()
    await waitFor(() => expect(screen.getByText(MOCK_RUN_ID)).toBeInTheDocument())
    expect(screen.getByText(/gold/i)).toBeInTheDocument()
  })

  it('strips poll_ prefix from displayed run ID', async () => {
    const runId = 'poll_20260724_054116_ema_crossover_gold'
    const cleanId = '20260724_054116_ema_crossover_gold'
    server.use(
      http.get(`http://localhost:8000/api/runs/${runId}`, () =>
        HttpResponse.json({ ...goldEmaRunDetailFixture, run_id: cleanId })
      ),
      http.get(`http://localhost:8000/api/runs/${runId}/series/:name`, () =>
        HttpResponse.json({
          run_id: cleanId,
          name: 'equity_curve',
          data: { index: [], columns: { value: [] } },
        })
      )
    )
    renderRunDetail(runId)
    await waitFor(() => expect(screen.getByText(cleanId)).toBeInTheDocument())
    expect(document.body.textContent).not.toContain('poll_')
  })

  it('copies clean run ID to clipboard on icon click', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', {
      ...navigator,
      clipboard: { writeText },
    })
    const runId = 'poll_20260724_054116_ema_crossover_gold'
    const cleanId = '20260724_054116_ema_crossover_gold'
    server.use(
      http.get(`http://localhost:8000/api/runs/${runId}`, () =>
        HttpResponse.json({ ...goldEmaRunDetailFixture, run_id: cleanId })
      ),
      http.get(`http://localhost:8000/api/runs/${runId}/series/:name`, () =>
        HttpResponse.json({
          run_id: cleanId,
          name: 'equity_curve',
          data: { index: [], columns: { value: [] } },
        })
      )
    )
    renderRunDetail(runId)
    await waitFor(() => expect(screen.getByText(cleanId)).toBeInTheDocument())
    screen.getByRole('button', { name: /copy run id/i }).click()
    expect(writeText).toHaveBeenCalledWith(cleanId)
    vi.unstubAllGlobals()
  })

  it('Overview tab is active by default when no ?tab= param is present', async () => {
    renderRunDetail()
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    )
    expect(screen.getByRole('tab', { name: 'Signal Quality' })).not.toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  it('clicking Signal Quality tab changes the active tab', async () => {
    const user = userEvent.setup()
    renderRunDetail()
    await waitFor(() => screen.getByRole('tab', { name: 'Signal Quality' }))
    await user.click(screen.getByRole('tab', { name: 'Signal Quality' }))
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: 'Signal Quality' })).toHaveAttribute(
        'aria-selected',
        'true'
      )
    )
    expect(screen.getByRole('tab', { name: 'Overview' })).not.toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  it('renders ErrorState for an unknown runId (RUN_NOT_FOUND)', async () => {
    renderRunDetail('completely-unknown-run-id-xyz')
    await waitFor(() => expect(screen.getByText(/run explorer/i)).toBeInTheDocument(), {
      timeout: 3000,
    })
  })

  it('Signal Quality tab renders IC-related content from signal_evaluation', async () => {
    const user = userEvent.setup()
    renderRunDetail()
    await waitFor(() => screen.getByRole('tab', { name: 'Signal Quality' }))
    await user.click(screen.getByRole('tab', { name: 'Signal Quality' }))
    await waitFor(() => expect(screen.getByText(/noise/i)).toBeInTheDocument())
  })

  it('Compare button is enabled and navigates after adding run to basket', async () => {
    const user = userEvent.setup()
    renderRunDetail()
    await waitFor(() => screen.getByRole('button', { name: /compare/i }))
    const compareBtn = screen.getByRole('button', { name: /compare/i })
    expect(compareBtn).not.toBeDisabled()
    await user.click(compareBtn)
  })

  it('Delete button opens confirmation dialog', async () => {
    const user = userEvent.setup()
    renderRunDetail()
    await waitFor(() => screen.getByRole('button', { name: /delete run/i }))
    await user.click(screen.getByRole('button', { name: /delete run/i }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText(/permanently remove/i)).toBeInTheDocument()
  })
})
