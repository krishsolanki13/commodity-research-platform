import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useAssets } from '@/api/hooks/useAssets'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useAssets', () => {
  it('returns universe response with 6 assets', async () => {
    const { result } = renderHook(() => useAssets(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.assets).toHaveLength(6)
    expect(result.current.data?.total_runs).toBe(12)
  })

  it('returns gold summary with correct last_price and health', async () => {
    const { result } = renderHook(() => useAssets(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.summaries.gold.last_price).toBe(1920.5)
    expect(result.current.data?.summaries.gold.data_health).toBe('ok')
  })

  it('copper summary has data_health="warn" and 2 flagged anomalies', async () => {
    const { result } = renderHook(() => useAssets(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.summaries.copper.data_health).toBe('warn')
    expect(result.current.data?.summaries.copper.flagged_anomalies).toBe(2)
  })
})
