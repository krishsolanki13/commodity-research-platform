import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, afterEach } from 'vitest'
import { usePortfolioAssets } from '@/api/hooks/usePortfolioAssets'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'
import { createWrapper } from '../../test-utils'
import { server } from '../../setup'

describe('usePortfolioAssets', () => {
  afterEach(() => {
    server.resetHandlers()
  })

  it('returns asset metrics for all 6 assets', async () => {
    const { result } = renderHook(() => usePortfolioAssets(MOCK_PORTFOLIO_RUN_ID), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(Object.keys(result.current.data?.asset_metrics ?? {})).toHaveLength(6)
    expect(result.current.data?.asset_metrics?.gold?.sharpe).toBeCloseTo(0.301)
  })

  it('is disabled when runId is an empty string', () => {
    const { result } = renderHook(() => usePortfolioAssets(''), {
      wrapper: createWrapper(),
    })

    expect(result.current.fetchStatus).toBe('idle')
  })
})
