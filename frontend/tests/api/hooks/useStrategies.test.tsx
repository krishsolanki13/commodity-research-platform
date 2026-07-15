import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useStrategies } from '@/api/hooks/useStrategies'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useStrategies', () => {
  it('returns strategy catalog with 4 strategies', async () => {
    const { result } = renderHook(() => useStrategies(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.strategies).toHaveLength(4)
  })

  it('ema_crossover default_params.fast_period === 50, slow_period === 200', async () => {
    const { result } = renderHook(() => useStrategies(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const ema = result.current.data?.strategies.find((s) => s.name === 'ema_crossover')
    expect(ema?.default_params.fast_period).toBe(50)
    expect(ema?.default_params.slow_period).toBe(200)
  })
})
