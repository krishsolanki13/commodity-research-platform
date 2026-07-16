import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { useBacktestStatus } from '@/api/hooks/useBacktestStatus'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useBacktestStatus', () => {
  it('returns complete status for known run id', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBacktestStatus(MOCK_RUN_ID), {
      wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('complete')
    expect(result.current.data?.run_id).toBe(MOCK_RUN_ID)
  })

  it('is disabled and returns no data when runId is null', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBacktestStatus(null), { wrapper })

    // enabled: false → query never fires
    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toBeUndefined()
  })

  it('stops polling once status reaches complete', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useBacktestStatus(MOCK_RUN_ID), {
      wrapper,
    })

    // MSW returns complete immediately for MOCK_RUN_ID
    await waitFor(() => expect(result.current.data?.status).toBe('complete'))

    // refetchInterval returned false → query is settled, not actively fetching
    expect(result.current.isFetching).toBe(false)
  })
})
