import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioDelete } from '@/api/hooks/usePortfolioDelete'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

describe('usePortfolioDelete', () => {
  it('mutation success removes portfolio cache entries', async () => {
    const { result } = renderHook(() => usePortfolioDelete(), {
      wrapper: createWrapper(),
    })
    result.current.mutate(MOCK_PORTFOLIO_RUN_ID)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.deleted).toBe(true)
    expect(result.current.data?.run_id).toBe(MOCK_PORTFOLIO_RUN_ID)
  })
})
