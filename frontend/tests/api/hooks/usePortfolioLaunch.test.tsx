import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioLaunch } from '@/api/hooks/usePortfolioLaunch'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

const BASE_REQUEST = {
  strategy: 'ema_crossover',
  params: { fast_period: 50, slow_period: 200 },
  initial_capital_per_asset: 1_000_000,
  commission_per_trade: 5,
  slippage_ticks: 1,
  sizing_method: 'fixed_notional' as const,
  notional_usd: 100_000,
  signal_threshold: 0,
}

describe('usePortfolioLaunch', () => {
  it('mutation returns run_id and queued status on 202', async () => {
    const { result } = renderHook(() => usePortfolioLaunch(), {
      wrapper: createWrapper(),
    })
    result.current.mutate(BASE_REQUEST)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.run_id).toBe(MOCK_PORTFOLIO_RUN_ID)
    expect(result.current.data?.status).toBe('queued')
  })

  it('mutation fires POST /api/portfolio/run with correct request body', async () => {
    const { result } = renderHook(() => usePortfolioLaunch(), {
      wrapper: createWrapper(),
    })
    const request = BASE_REQUEST
    result.current.mutate(request)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.variables).toMatchObject(request)
  })
})
