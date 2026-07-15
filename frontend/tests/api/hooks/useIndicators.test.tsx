import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useIndicators } from '@/api/hooks/useIndicators'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useIndicators', () => {
  it('returns indicator catalog with 5 indicators (sma, ema, rsi, rvgi, momentum)', async () => {
    const { result } = renderHook(() => useIndicators(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.indicators).toHaveLength(5)
    const names = result.current.data?.indicators.map((i) => i.name) ?? []
    expect(names).toEqual(expect.arrayContaining(['sma', 'ema', 'rsi', 'rvgi', 'momentum']))
  })

  it('each indicator has params_schema with at least one ParamSpec', async () => {
    const { result } = renderHook(() => useIndicators(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    for (const indicator of result.current.data?.indicators ?? []) {
      expect(indicator.params_schema.length).toBeGreaterThanOrEqual(1)
    }
  })
})
