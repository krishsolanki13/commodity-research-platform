import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useCurveSnapshots } from '@/api/hooks/useCurveSnapshots'

beforeEach(() => qc.clear())

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('useCurveSnapshots', () => {
  it('returns parallel results for 2 assets (gold + silver)', async () => {
    const { result } = renderHook(() => useCurveSnapshots(['gold', 'silver'], 4), { wrapper })
    await waitFor(() => expect(result.current.every((r) => r.isSuccess || r.isError)).toBe(true), {
      timeout: 5000,
    })
    expect(result.current).toHaveLength(2)
    expect(result.current[0].isSuccess).toBe(true)
    expect(result.current[0].data?.asset).toBe('gold')
  })

  it('returns empty array for empty assets list', () => {
    const { result } = renderHook(() => useCurveSnapshots([], 4), { wrapper })
    expect(result.current).toHaveLength(0)
  })
})
