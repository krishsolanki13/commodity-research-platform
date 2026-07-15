import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient as qc } from '@/app/queryClient'
import { server } from '../setup'
import { http, HttpResponse } from 'msw'
import AssetDetailScreen from '@/screens/market/AssetDetail'

function Wrapper({ asset = 'gold' }: { asset?: string }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/market/${asset}`]}>
        <Routes>
          <Route path="/market/:asset" element={<AssetDetailScreen />} />
          <Route path="/market" element={<div>Market</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => qc.clear())

describe('AssetDetailScreen', () => {
  it('renders asset header for gold', async () => {
    render(<Wrapper asset="gold" />)
    await waitFor(
      () => expect(screen.getAllByText(/GC=F/i).length).toBeGreaterThan(0),
      { timeout: 5000 }
    )
    expect(screen.getByRole('heading', { name: /gold/i })).toBeInTheDocument()
  })

  it('renders "Open in Workbench" link with correct href', async () => {
    render(<Wrapper asset="gold" />)
    await waitFor(
      () => expect(screen.getByRole('link', { name: /open in workbench/i })).toBeInTheDocument(),
      { timeout: 5000 }
    )
    const link = screen.getByRole('link', { name: /open in workbench/i })
    expect(link.getAttribute('href')).toContain('/research')
    expect(link.getAttribute('href')).toContain('asset=gold')
  })

  it('renders error state for unknown asset slug', async () => {
    server.use(
      http.get('http://localhost:8000/api/assets/notanasset/summary', () =>
        HttpResponse.json(
          { error: { code: 'ASSET_NOT_FOUND', message: "Asset 'notanasset' not found." } },
          { status: 404 }
        )
      ),
      http.get('http://localhost:8000/api/assets/notanasset/ohlcv', () =>
        HttpResponse.json(
          { error: { code: 'ASSET_NOT_FOUND', message: "Asset 'notanasset' not found." } },
          { status: 404 }
        )
      )
    )
    render(<Wrapper asset="notanasset" />)
    await waitFor(
      () => expect(document.body.innerHTML).toMatch(/error|not found|asset_not_found/i),
      { timeout: 5000 }
    )
  })

  it('metrics panel renders without crash', async () => {
    render(<Wrapper asset="gold" />)
    await waitFor(() => expect(screen.getByText('LAST')).toBeInTheDocument(), { timeout: 5000 })
    expect(screen.getByText('BARS')).toBeInTheDocument()
  })
})
