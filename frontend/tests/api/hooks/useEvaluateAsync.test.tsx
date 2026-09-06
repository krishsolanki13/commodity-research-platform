import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { qk } from '@/api/queryKeys'
import {
  useEvaluateAsyncLaunch,
  useEvaluateAsyncStatus,
  useEvaluateAsyncResult,
} from '@/api/hooks/useEvaluateAsync'
import type { components } from '@/api/schema'

type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

describe('useEvaluateAsync', () => {
  it('launch mutation posts evaluate-async and returns job_id', async () => {
    const { result } = renderHook(() => useEvaluateAsyncLaunch(), { wrapper })
    const launched = await result.current.mutateAsync({
      asset: 'gold',
      strategy: 'carry',
      params: { threshold: 0.0, n_contracts: 4 },
      from_date: '2015-01-01',
      to_date: '2026-07-15',
    })
    expect(launched.job_id).toBe('eval-async-test-job')
    expect(launched.status).toBe('queued')
  })

  it('status query fetches and stops when complete (staleTime 0)', async () => {
    const { result } = renderHook(() => useEvaluateAsyncStatus('eval-async-test-job'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('complete')
    expect(result.current.data?.job_id).toBe('eval-async-test-job')
    expect(qc.getQueryState(qk.evaluateAsync.status('eval-async-test-job'))?.dataUpdateCount).toBeGreaterThan(0)
  })

  it('result query is disabled until enabled=true, then returns evaluation', async () => {
    const disabled = renderHook(
      ({ enabled }: { enabled: boolean }) => useEvaluateAsyncResult('eval-async-test-job', enabled),
      { wrapper, initialProps: { enabled: false } }
    )
    expect(disabled.result.current.fetchStatus).toBe('idle')
    expect(disabled.result.current.data).toBeUndefined()

    disabled.rerender({ enabled: true })
    await waitFor(() => expect(disabled.result.current.isSuccess).toBe(true))
    const data = disabled.result.current.data as SignalEvaluateResponse
    expect(data.evaluation.ic).toBe(0.0123)
    expect(qc.getQueryData(qk.evaluateAsync.result('eval-async-test-job'))).toBeDefined()
  })
})
