import { useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiClientError, client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type FeatureComputeResponse = components['schemas']['FeatureComputeResponse']
type SignalGenerateResponse = components['schemas']['SignalGenerateResponse']
type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']
type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']

export interface EvaluateChainParams {
  asset: string
  strategy: string
  params: Record<string, unknown>
  featureSpecs: FeatureSpecRequest[]
  fromDate: string
  toDate: string
}

export interface EvaluateChainResult {
  features: FeatureComputeResponse
  signal: SignalGenerateResponse
  evaluation: SignalEvaluateResponse
  evaluatedAt: string
}

export interface EvaluateChainAsyncLaunch {
  features: FeatureComputeResponse
  signal: SignalGenerateResponse
  job_id: string
}

export type EvaluateChainOutcome = EvaluateChainResult | EvaluateChainAsyncLaunch

export function isEvaluateChainAsyncLaunch(
  result: EvaluateChainOutcome,
): result is EvaluateChainAsyncLaunch {
  return 'job_id' in result
}

type ProgressStep = {
  step: 'features' | 'signal' | 'evaluation'
  stepIndex: 1 | 2 | 3
}

function isAsyncEvaluateStrategy(strategy: string): boolean {
  return strategy === 'carry'
}

function isAsyncRequiredError(error: unknown): boolean {
  return error instanceof ApiClientError && error.apiError.code === 'ASYNC_REQUIRED_STRATEGY'
}

// Q7 ruling: onProgress passed as hook param, held in ref — keeps mutateAsync params serializable
export function useEvaluateChainMutation(onProgress?: (step: ProgressStep) => void) {
  const onProgressRef = useRef(onProgress)
  useEffect(() => {
    onProgressRef.current = onProgress
  }, [onProgress])

  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (p: EvaluateChainParams): Promise<EvaluateChainOutcome> => {
      // Step 1: Compute features (skip when strategy needs no indicator columns —
      // empty specs → API 400 NO_INDICATORS, which previously aborted the chain silently)
      let features: FeatureComputeResponse
      if (p.featureSpecs.length === 0) {
        features = {
          asset: p.asset,
          from_date: p.fromDate,
          to_date: p.toDate,
          bars: 0,
          specs: [],
          columns: { index: [], columns: {} },
        }
      } else {
        onProgressRef.current?.({ step: 'features', stepIndex: 1 })
        features = await client.post<FeatureComputeResponse>('/api/features/compute', {
          asset: p.asset,
          from_date: p.fromDate,
          to_date: p.toDate,
          specs: p.featureSpecs,
        })
        queryClient.setQueryData(qk.features(p.asset, p.fromDate, p.toDate, p.featureSpecs), features)
      }

      // Step 2: Generate signal
      onProgressRef.current?.({ step: 'signal', stepIndex: 2 })
      const signal = await client.post<SignalGenerateResponse>('/api/signals/generate', {
        asset: p.asset,
        strategy: p.strategy,
        params: p.params,
        from_date: p.fromDate,
        to_date: p.toDate,
      })
      queryClient.setQueryData(qk.signalGenerate(p.asset, p.strategy, p.params), signal)

      // Step 3: Evaluate signal — Carry (and ASYNC_REQUIRED fallback) use the async job path
      onProgressRef.current?.({ step: 'evaluation', stepIndex: 3 })
      const evalPayload = {
        asset: p.asset,
        strategy: p.strategy,
        params: p.params,
        from_date: p.fromDate,
        to_date: p.toDate,
      }

      if (isAsyncEvaluateStrategy(p.strategy)) {
        const launched = await client.post<{ job_id: string; status: string }>(
          '/api/signals/evaluate-async',
          evalPayload,
        )
        return {
          features,
          signal,
          job_id: launched.job_id,
        }
      }

      try {
        const evaluation = await client.post<SignalEvaluateResponse>(
          '/api/signals/evaluate',
          evalPayload,
        )
        queryClient.setQueryData(qk.signalEvaluate(p.asset, p.strategy, p.params), evaluation)

        return {
          features,
          signal,
          evaluation,
          evaluatedAt: new Date().toISOString(),
        }
      } catch (error) {
        if (!isAsyncRequiredError(error)) throw error
        const launched = await client.post<{ job_id: string; status: string }>(
          '/api/signals/evaluate-async',
          evalPayload,
        )
        return {
          features,
          signal,
          job_id: launched.job_id,
        }
      }
    },
  })
}
