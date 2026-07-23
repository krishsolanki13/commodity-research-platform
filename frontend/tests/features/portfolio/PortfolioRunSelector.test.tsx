import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PortfolioRunSelector } from '@/features/portfolio/PortfolioRunSelector'
import { server } from '../../setup'
import { http, HttpResponse } from 'msw'

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
    localStorage.clear()
  })

  it('renders null when API returns no runs', async () => {
    server.use(
      http.get('http://localhost:8000/api/portfolio/runs', () =>
        HttpResponse.json({ runs: [], total: 0 })
      )
    )
    const { container } = render(<PortfolioRunSelector />, { wrapper: Wrapper })
    await waitFor(() => expect(container.firstChild).toBeNull())
  })

  it('renders Select when API returns runs', async () => {
    render(<PortfolioRunSelector />, { wrapper: Wrapper })
    await waitFor(() => screen.getByRole('combobox'))
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })
})
