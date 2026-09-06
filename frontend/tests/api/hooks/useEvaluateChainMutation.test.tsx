import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { http, HttpResponse } from 'msw'
import { queryClient as qc } from '@/app/queryClient'
import { qk } from '@/api/queryKeys'
import {
  useEvaluateChainMutation,
  isEvaluateChainAsyncLaunch,
} from '@/api/hooks/useEvaluateChainMutation'
import { server } from '../../setup'
import type { components } from '@/api/schema'

type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const validParams = {
  asset: 'gold',
  strategy: 'ema_crossover',
  params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
  featureSpecs: [
    { name: 'ema', params: { period: 50 } },
    { name: 'ema', params: { period: 200 } },
  ],
  fromDate: '2015-01-01',
  toDate: '2026-07-15',
}

beforeEach(() => qc.clear())

describe('useEvaluateChainMutation', () => {
  it('mutateAsync resolves with EvaluateChainResult containing features, signal, evaluation', async () => {
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    const chain = await result.current.mutateAsync(validParams)
    expect(isEvaluateChainAsyncLaunch(chain)).toBe(false)
    if (isEvaluateChainAsyncLaunch(chain)) return
    expect(chain.features).toBeDefined()
    expect(chain.signal).toBeDefined()
    expect(chain.evaluation).toBeDefined()
    expect(chain.evaluatedAt).toBeDefined()
  })

  it('onProgress called in order features→signal→evaluation', async () => {
    const steps: string[] = []
    const { result } = renderHook(() => useEvaluateChainMutation((s) => steps.push(s.step)), {
      wrapper,
    })
    await result.current.mutateAsync(validParams)
    expect(steps).toEqual(['features', 'signal', 'evaluation'])
  })

  it('after successful chain, queryClient has signalEvaluate data', async () => {
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    await result.current.mutateAsync(validParams)
    const cached = qc.getQueryData(qk.signalEvaluate('gold', 'ema_crossover', validParams.params))
    expect(cached).toBeDefined()
  })

  it('Gold EMA eval ic_band === noise (ic = 0.0123)', async () => {
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    await result.current.mutateAsync(validParams)
    const cached = qc.getQueryData<SignalEvaluateResponse>(
      qk.signalEvaluate('gold', 'ema_crossover', validParams.params)
    )
    expect(cached?.evaluation.ic).toBe(0.0123)
    expect(cached?.evaluation.ic_band).toBe('noise')
  })

  it('mutation throws when signal/evaluate endpoint returns 400', async () => {
    server.use(
      http.post('http://localhost:8000/api/signals/evaluate', () =>
        HttpResponse.json({}, { status: 400 })
      )
    )
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    await expect(result.current.mutateAsync(validParams)).rejects.toThrow()
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it('after evaluate failure, queryClient has no data at signalEvaluate key', async () => {
    server.use(
      http.post('http://localhost:8000/api/signals/evaluate', () =>
        HttpResponse.json({}, { status: 400 })
      )
    )
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    await expect(result.current.mutateAsync(validParams)).rejects.toThrow()
    const cached = qc.getQueryData(qk.signalEvaluate('gold', 'ema_crossover', validParams.params))
    expect(cached).toBeUndefined()
  })

  it('skips features/compute when featureSpecs is empty (featureless strategies)', async () => {
    let featuresCalled = false
    server.use(
      http.post('http://localhost:8000/api/features/compute', () => {
        featuresCalled = true
        return HttpResponse.json(
          { error: { code: 'NO_INDICATORS', message: 'At least one indicator spec is required.' } },
          { status: 400 }
        )
      })
    )
    const steps: string[] = []
    const { result } = renderHook(() => useEvaluateChainMutation((s) => steps.push(s.step)), {
      wrapper,
    })
    const chain = await result.current.mutateAsync({
      asset: 'gold',
      strategy: 'donchian_breakout',
      params: { channel_period: 20 },
      featureSpecs: [],
      fromDate: '2015-01-01',
      toDate: '2026-07-15',
    })
    expect(featuresCalled).toBe(false)
    expect(steps).toEqual(['signal', 'evaluation'])
    expect(isEvaluateChainAsyncLaunch(chain)).toBe(false)
    if (isEvaluateChainAsyncLaunch(chain)) return
    expect(chain.features.specs).toEqual([])
    expect(chain.signal).toBeDefined()
    expect(chain.evaluation).toBeDefined()
  })

  it('routes carry to evaluate-async and returns job_id without hitting sync evaluate', async () => {
    let asyncCalled = false
    let syncCalled = false
    server.use(
      http.post('http://localhost:8000/api/signals/evaluate-async', () => {
        asyncCalled = true
        return HttpResponse.json({ job_id: 'job-carry-1', status: 'queued' }, { status: 202 })
      }),
      http.post('http://localhost:8000/api/signals/evaluate', () => {
        syncCalled = true
        return HttpResponse.json({}, { status: 400 })
      })
    )
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    const chain = await result.current.mutateAsync({
      asset: 'gold',
      strategy: 'carry',
      params: { threshold: 0.0, n_contracts: 4 },
      featureSpecs: [],
      fromDate: '2015-01-01',
      toDate: '2026-07-15',
    })
    expect(asyncCalled).toBe(true)
    expect(syncCalled).toBe(false)
    expect(isEvaluateChainAsyncLaunch(chain)).toBe(true)
    if (!isEvaluateChainAsyncLaunch(chain)) return
    expect(chain.job_id).toBe('job-carry-1')
    expect(chain.signal).toBeDefined()
  })

  it('falls back to evaluate-async when sync evaluate returns ASYNC_REQUIRED_STRATEGY', async () => {
    let asyncCalled = false
    server.use(
      http.post('http://localhost:8000/api/signals/evaluate', () =>
        HttpResponse.json(
          { error: { code: 'ASYNC_REQUIRED_STRATEGY', message: 'requires async evaluation' } },
          { status: 400 }
        )
      ),
      http.post('http://localhost:8000/api/signals/evaluate-async', () => {
        asyncCalled = true
        return HttpResponse.json({ job_id: 'job-fallback-1', status: 'queued' }, { status: 202 })
      })
    )
    const { result } = renderHook(() => useEvaluateChainMutation(), { wrapper })
    const chain = await result.current.mutateAsync(validParams)
    expect(asyncCalled).toBe(true)
    expect(isEvaluateChainAsyncLaunch(chain)).toBe(true)
    if (!isEvaluateChainAsyncLaunch(chain)) return
    expect(chain.job_id).toBe('job-fallback-1')
  })
})
