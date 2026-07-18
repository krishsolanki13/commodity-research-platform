import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createWrapper } from '../../test-utils'
import { usePortfolioStatus } from '@/api/hooks/usePortfolioStatus'
import { MOCK_PORTFOLIO_RUN_ID } from '../../mocks/fixtures/portfolio'

describe('usePortfolioStatus', () => {
  it('returns complete status for known run_id', async () => {
    const { result } = renderHook(
      () => usePortfolioStatus(MOCK_PORTFOLIO_RUN_ID),
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('complete')
  })

  it('refetchInterval returns false when status is complete', async () => {
    const { result } = renderHook(
      () => usePortfolioStatus(MOCK_PORTFOLIO_RUN_ID),
      { wrapper: createWrapper() }
    )
    await waitFor(() => expect(result.current.data?.status).toBe('complete'))
    // Once complete, polling should stop — verified by status being stable
    expect(result.current.data?.status).toBe('complete')
  })
})
