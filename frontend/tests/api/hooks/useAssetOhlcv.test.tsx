import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useAssetOhlcv', () => {
  it('returns OhlcvResponse with ColumnarSeries for gold', async () => {
    const { result } = renderHook(
      () =>
        useAssetOhlcv('gold', {
          from_date: '2026-06-13',
          to_date: '2026-07-06',
          downsample: 'view',
        }),
      { wrapper }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.asset).toBe('gold')
    expect(result.current.data?.data.index).toHaveLength(20)
    expect(result.current.data?.data.index[0]).toBeGreaterThan(1_000_000_000_000)
  })

  it('enters error state for unknown asset', async () => {
    const { result } = renderHook(() => useAssetOhlcv('notanasset', {}), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 })
    expect(result.current.error).toBeDefined()
  })

  it('remains idle when asset is empty string', () => {
    const { result } = renderHook(() => useAssetOhlcv('', {}), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
