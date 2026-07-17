import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { describe, it, expect } from 'vitest'
import { useCurveAvailableAssets } from '@/api/hooks/useCurveAvailableAssets'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { wrapper, queryClient }
}

describe('useCurveAvailableAssets', () => {
  it('returns the list of assets with contract data', async () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCurveAvailableAssets(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.assets).toContain('gold')
    expect(result.current.data?.assets).toContain('natural_gas')
    expect(result.current.data?.assets).toHaveLength(6)
  })

  it('data remains fresh indefinitely (staleTime: Infinity)', async () => {
    const { wrapper } = createWrapper()
    const { result } = renderHook(() => useCurveAvailableAssets(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // With staleTime: Infinity the data is never marked stale after load
    expect(result.current.isStale).toBe(false)
  })
})
