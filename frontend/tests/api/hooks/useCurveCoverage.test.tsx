import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { qk } from '@/api/queryKeys'
import { useCurveCoverage } from '@/api/hooks/useCurveCoverage'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useCurveCoverage', () => {
  it('fetches coverage for carry and caches under qk.curveCoverage', async () => {
    const { result } = renderHook(() => useCurveCoverage('gold', 'carry'), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.asset).toBe('gold')
    expect(result.current.data?.curve_coverage_start).toBe('2024-09-27')
    expect(qc.getQueryData(qk.curveCoverage('gold'))).toBeDefined()
  })

  it('does not fetch when strategy is not carry', () => {
    const { result } = renderHook(() => useCurveCoverage('gold', 'ema_crossover'), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
    expect(result.current.data).toBeUndefined()
  })

  it('does not fetch when asset is null', () => {
    const { result } = renderHook(() => useCurveCoverage(null, 'carry'), { wrapper })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
