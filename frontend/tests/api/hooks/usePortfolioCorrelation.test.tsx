import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioCorrelation } from '@/api/hooks/usePortfolioCorrelation'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

describe('usePortfolioCorrelation', () => {
  it('returns correlation report with WTI-Brent correlation = 0.62', async () => {
    const { result } = renderHook(
      () => usePortfolioCorrelation(MOCK_PORTFOLIO_RUN_ID),
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const matrix = result.current.data?.correlation_matrix
    expect(matrix?.wti?.brent).toBe(0.62)
  })
})
