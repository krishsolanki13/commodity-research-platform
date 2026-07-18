import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioRisk } from '@/api/hooks/usePortfolioRisk'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

describe('usePortfolioRisk', () => {
  it('returns risk report with portfolio_var_99 = 44490', async () => {
    const { result } = renderHook(
      () => usePortfolioRisk(MOCK_PORTFOLIO_RUN_ID),
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.portfolio_var_99).toBe(44490)
  })
})
