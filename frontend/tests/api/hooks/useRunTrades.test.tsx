import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { http, HttpResponse } from 'msw'
import { server } from '../../setup'
import { useRunTrades } from '@/api/hooks/useRunTrades'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'
import { goldTradesFixture } from '../../mocks/fixtures/run-trades'

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useRunTrades', () => {
  it('returns paginated trades with trade records and stats', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(
      () => useRunTrades(MOCK_RUN_ID, 1),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.trades).toHaveLength(10)
    expect(result.current.data?.stats.n_trades).toBe(19)
    expect(result.current.data?.page).toBe(1)
    expect(result.current.data?.total).toBe(19)
    expect(result.current.data?.page_size).toBe(100)
  })

  it('includes page=2 in the request query string when page 2 is requested', async () => {
    let capturedUrl = ''

    server.use(
      http.get(
        `http://localhost:8000/api/runs/${MOCK_RUN_ID}/trades`,
        ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(goldTradesFixture)
        }
      )
    )

    const wrapper = createWrapper()
    const { result } = renderHook(
      () => useRunTrades(MOCK_RUN_ID, 2),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(capturedUrl).toContain('page=2')
    expect(capturedUrl).toContain('page_size=100')
  })
})
