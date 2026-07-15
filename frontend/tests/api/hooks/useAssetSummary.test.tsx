import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useAssetSummary } from '@/api/hooks/useAssetSummary'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useAssetSummary', () => {
  it('returns gold summary with correct health and bar count', async () => {
    const { result } = renderHook(() => useAssetSummary('gold'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.data_health).toBe('ok')
    expect(result.current.data?.bar_count).toBe(4150)
  })

  it('enters error state for unknown asset', async () => {
    const { result } = renderHook(() => useAssetSummary('unknown_xyz'), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 })
  })
})
