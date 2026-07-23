import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioEquity } from '@/api/hooks/usePortfolioEquity'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

describe('usePortfolioEquity', () => {
  it('returns portfolio equity ColumnarSeries', async () => {
    const { result } = renderHook(() => usePortfolioEquity(MOCK_PORTFOLIO_RUN_ID), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.portfolio_equity).toBeDefined()
    expect(result.current.data?.portfolio_equity.index).toHaveLength(4)
  })
})
