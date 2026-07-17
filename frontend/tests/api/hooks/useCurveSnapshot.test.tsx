import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { describe, it, expect } from 'vitest'
import { useCurveSnapshot } from '@/api/hooks/useCurveSnapshot'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { wrapper, queryClient }
}

describe('useCurveSnapshot', () => {
  it('returns FuturesCurveResponse with regime and curve points for Gold', async () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCurveSnapshot('gold', 6), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.asset).toBe('gold')
    expect(result.current.data?.regime).toBe('contango')
    expect(result.current.data?.points).toHaveLength(4)
    expect(result.current.data?.front_price).toBeGreaterThan(0)
  })

  it('is disabled (fetchStatus: idle) when asset is empty string', () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCurveSnapshot(''), { wrapper })

    // enabled: !!asset evaluates to false for empty string
    expect(result.current.fetchStatus).toBe('idle')
  })
})
