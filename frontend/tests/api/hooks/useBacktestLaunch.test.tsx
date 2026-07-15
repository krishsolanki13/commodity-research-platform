import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi } from 'vitest'
import React from 'react'
import { http, HttpResponse } from 'msw'
import { server } from '../../setup'
import { useBacktestLaunch } from '@/api/hooks/useBacktestLaunch'
import { MOCK_RUN_ID } from '../../mocks/fixtures/run-detail'

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, Wrapper }
}

const BASE_REQUEST = {
  asset: 'gold',
  strategy: 'ema_crossover',
  params: { fast_period: 50, slow_period: 200 },
  initial_capital: 1_000_000,
  commission_per_trade: 5,
  slippage_ticks: 1,
  sizing_method: 'fixed_notional' as const,
  notional_usd: 100_000,
  signal_threshold: 0,
}

describe('useBacktestLaunch', () => {
  it('returns run_id and queued status on successful launch', async () => {
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useBacktestLaunch(), {
      wrapper: Wrapper,
    })

    let data: unknown
    await act(async () => {
      data = await result.current.mutateAsync(BASE_REQUEST)
    })

    expect(data).toMatchObject({ run_id: MOCK_RUN_ID, status: 'queued' })
  })

  it('invalidates the runs list query on success', async () => {
    const { qc, Wrapper } = createWrapper()
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries')

    const { result } = renderHook(() => useBacktestLaunch(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync(BASE_REQUEST)
    })

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalled())
  })

  it('sends signal_evaluation: null in request body when IC Gate is overridden', async () => {
    let capturedBody: Record<string, unknown> = {}

    server.use(
      http.post('http://localhost:8000/api/backtests', async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(
          { run_id: MOCK_RUN_ID, status: 'queued' },
          { status: 202 }
        )
      })
    )

    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useBacktestLaunch(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync({
        ...BASE_REQUEST,
        signal_evaluation: null,
      })
    })

    expect(capturedBody.signal_evaluation).toBeNull()
  })
})
