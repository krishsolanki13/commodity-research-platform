import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, afterEach } from 'vitest'
import React from 'react'
import { useRunDetail } from '@/api/hooks/useRunDetail'
import { ApiClientError } from '@/api/client'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'
import { server } from '../../setup'

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useRunDetail', () => {
  afterEach(() => {
    server.resetHandlers()
  })

  it('returns run detail with correct scalar metrics', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunDetail(MOCK_RUN_ID), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(result.current.data?.asset).toBe('gold')
    expect(result.current.data?.strategy).toBe('ema_crossover')
    expect(result.current.data?.metrics.sharpe).toBeCloseTo(0.301, 2)
    expect(result.current.data?.metrics.initial_capital).toBe(1_000_000)
  })

  it('returns signal_evaluation with correct ic_band', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunDetail(MOCK_RUN_ID), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(result.current.data?.signal_evaluation?.ic_band).toBe('noise')
    expect(result.current.data?.signal_evaluation?.ic).toBeCloseTo(0.0123, 4)
    expect(result.current.data?.signal_evaluation?.decay).toHaveLength(5)
  })

  it('surfaces an ApiClientError for an unknown run id (RUN_NOT_FOUND)', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunDetail('unknown-run-id-99999'), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })
    expect(result.current.error).toBeInstanceOf(ApiClientError)
  })
})
