import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { server } from '../setup'
import { RunExplorer } from '@/screens/runs/RunExplorer'
import { useComparisonBasket } from '@/stores/comparisonBasket'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper() {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/runs']}>
        <Routes>
          <Route path="/runs" element={<RunExplorer />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RunExplorer', () => {
  beforeEach(() => {
    qc.clear()
    useComparisonBasket.setState({ ids: [] })
  })

  it('renders run table with 2 runs from runListFixture', async () => {
    render(<Wrapper />)
    await waitFor(() => {
      const bodyRows = screen
        .getAllByRole('row')
        .filter((r) => r.closest('tbody') !== null)
      expect(bodyRows).toHaveLength(2)
    })
  })

  it('strategy filter dropdown is present', async () => {
    render(<Wrapper />)
    await waitFor(() =>
      expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0)
    )
  })

  it('checking a run row checkbox adds to comparison basket', async () => {
    render(<Wrapper />)
    await waitFor(() => {
      const bodyRows = screen
        .getAllByRole('row')
        .filter((r) => r.closest('tbody') !== null)
      expect(bodyRows).toHaveLength(2)
    })
    const checkboxes = screen.getAllByRole('checkbox')
    // checkboxes[0] is the select-all header; checkboxes[1] is the first data row
    await userEvent.click(checkboxes[1])
    expect(useComparisonBasket.getState().ids).toHaveLength(1)
  })

  it('loading state renders without crashing', () => {
    const { container } = render(<Wrapper />)
    // Container must be non-null during loading phase
    expect(container.firstChild).not.toBeNull()
  })

  it('empty runs response shows EmptyState', async () => {
    server.use(
      http.get('http://localhost:8000/api/runs', () =>
        HttpResponse.json({ runs: [], total: 0, page: 1, page_size: 50 })
      )
    )
    const emptyQc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    render(
      <QueryClientProvider client={emptyQc}>
        <MemoryRouter initialEntries={['/runs']}>
          <Routes>
            <Route path="/runs" element={<RunExplorer />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
    await waitFor(() =>
      expect(screen.getByText(/no runs yet/i)).toBeInTheDocument()
    )
  })
})
