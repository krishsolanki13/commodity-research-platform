import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioSummary } from '@/api/hooks/usePortfolioSummary'
import {
  MOCK_PORTFOLIO_RUN_ID,
  portfolioSummaryFixture,
} from '../../mocks/fixtures/portfolio'

describe('usePortfolioSummary', () => {
  it('returns portfolio summary with correct portfolio_metrics', async () => {
    const { result } = renderHook(
      () => usePortfolioSummary(MOCK_PORTFOLIO_RUN_ID),
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.portfolio_metrics.sharpe).toBe(
      portfolioSummaryFixture.portfolio_metrics.sharpe
    )
    expect(result.current.data?.initial_capital_total).toBe(6_000_000)
  })
})
