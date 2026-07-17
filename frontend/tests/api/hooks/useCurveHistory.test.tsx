import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { describe, it, expect } from 'vitest'
import { useCurveHistory } from '@/api/hooks/useCurveHistory'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { wrapper, queryClient }
}

describe('useCurveHistory', () => {
  it('returns CurveHistoryResponse with 10 snapshots for Gold', async () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(
      () => useCurveHistory('gold', '2025-07-15', '2026-07-15', 6),
      { wrapper }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.asset).toBe('gold')
    expect(result.current.data?.snapshots).toHaveLength(10)
    expect(result.current.data?.snapshots[0]).toHaveProperty('observation_date')
    expect(result.current.data?.snapshots[0]).toHaveProperty('regime')
  })

  it('is disabled (fetchStatus: idle) when asset is empty string', () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(
      () => useCurveHistory('', '2025-07-15', '2026-07-15', 6),
      { wrapper }
    )

    // enabled: !!asset && !!fromDate && !!toDate → false when asset is ''
    expect(result.current.fetchStatus).toBe('idle')
  })
})
