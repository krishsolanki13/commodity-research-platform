import { useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
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

type ProgressStep = {
  step: 'features' | 'signal' | 'evaluation'
  stepIndex: 1 | 2 | 3
}

// Q7 ruling: onProgress passed as hook param, held in ref — keeps mutateAsync params serializable
export function useEvaluateChainMutation(onProgress?: (step: ProgressStep) => void) {
  const onProgressRef = useRef(onProgress)
  useEffect(() => {
    onProgressRef.current = onProgress
  }, [onProgress])

  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (p: EvaluateChainParams): Promise<EvaluateChainResult> => {
      // Step 1: Compute features
      onProgressRef.current?.({ step: 'features', stepIndex: 1 })
      const features = await client.post<FeatureComputeResponse>('/api/features/compute', {
        asset: p.asset,
        from_date: p.fromDate,
        to_date: p.toDate,
        specs: p.featureSpecs,
      })
      queryClient.setQueryData(qk.features(p.asset, p.fromDate, p.toDate, p.featureSpecs), features)

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

      // Step 3: Evaluate signal
      onProgressRef.current?.({ step: 'evaluation', stepIndex: 3 })
      const evaluation = await client.post<SignalEvaluateResponse>('/api/signals/evaluate', {
        asset: p.asset,
        strategy: p.strategy,
        params: p.params,
        from_date: p.fromDate,
        to_date: p.toDate,
      })
      queryClient.setQueryData(qk.signalEvaluate(p.asset, p.strategy, p.params), evaluation)

      return {
        features,
        signal,
        evaluation,
        evaluatedAt: new Date().toISOString(),
      }
    },
  })
}
