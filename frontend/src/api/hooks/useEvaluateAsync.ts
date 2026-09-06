// Async signal evaluation — POST → poll status → GET result
// Used for slow strategies (Carry). The synchronous POST /api/signals/evaluate
// remains the path for all other strategies and is unchanged.

import { useMutation, useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type SignalEvaluateRequest = components['schemas']['SignalEvaluateRequest']
type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']

// Backend returns untyped dicts (OpenAPI additionalProperties). Local types
// match the documented evaluate-async contract.
export type EvaluateAsyncJobStatus = 'queued' | 'running' | 'complete' | 'failed'

export interface EvaluateAsyncLaunchResponse {
  job_id: string
  status: string
}

export interface EvaluateAsyncJobStatusResponse {
  job_id: string
  status: EvaluateAsyncJobStatus
  error?: string
}

// Step 1: Launch the async job
export function useEvaluateAsyncLaunch() {
  return useMutation({
    mutationFn: (
      request: SignalEvaluateRequest,
    ): Promise<EvaluateAsyncLaunchResponse> =>
      client.post('/api/signals/evaluate-async', request),
  })
}

// Step 2: Poll job status until complete or failed
export function useEvaluateAsyncStatus(jobId: string | null) {
  return useQuery({
    queryKey: qk.evaluateAsync.status(jobId!),
    queryFn: (): Promise<EvaluateAsyncJobStatusResponse> =>
      client.get(`/api/signals/evaluate-async/${jobId}/status`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s !== 'complete' && s !== 'failed' ? 2000 : false
    },
    staleTime: 0,
  })
}

// Step 3: Fetch result once status === 'complete'
export function useEvaluateAsyncResult(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: qk.evaluateAsync.result(jobId!),
    queryFn: (): Promise<SignalEvaluateResponse> =>
      client.get(`/api/signals/evaluate-async/${jobId}/result`),
    enabled: !!jobId && enabled,
    staleTime: Infinity,
  })
}
