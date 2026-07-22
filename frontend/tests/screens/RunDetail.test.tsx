import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import RunDetail from '@/screens/runs/RunDetail'
import { MOCK_RUN_ID } from '../mocks/fixtures/run-detail'

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
})
