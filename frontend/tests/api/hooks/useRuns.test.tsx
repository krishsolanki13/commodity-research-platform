import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useRuns } from '@/api/hooks/useRuns'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useRuns', () => {
  it('returns run list with correct shape', async () => {
    const { result } = renderHook(() => useRuns({ asset: 'gold', page_size: 5 }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.runs).toBeDefined()
    expect(Array.isArray(result.current.data?.runs)).toBe(true)
  })

  it('returns fixture runs without errors', async () => {
    const { result } = renderHook(() => useRuns({ asset: 'silver', page_size: 5 }), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.runs).toHaveLength(2)
  })
})
