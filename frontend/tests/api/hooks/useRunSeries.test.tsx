import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { useRunSeries } from '@/api/hooks/useRunSeries'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useRunSeries', () => {
  it('returns equity_curve series with index and value arrays', async () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunSeries(MOCK_RUN_ID, 'equity_curve'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.name).toBe('equity_curve')
    expect(result.current.data?.run_id).toBe(MOCK_RUN_ID)
    expect(Array.isArray(result.current.data?.data.index)).toBe(true)
    expect(Array.isArray(result.current.data?.data.columns.value)).toBe(true)
    expect(result.current.data?.data.index.length).toBeGreaterThan(0)
    expect(result.current.data?.data.columns.value.length).toBe(
      result.current.data?.data.index.length
    )
  })

  it('is disabled and returns no data when runId is empty string', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => useRunSeries('', 'equity_curve'), { wrapper })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toBeUndefined()
  })
})
