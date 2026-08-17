// Async regime attribution — POST → poll status → GET result
// Replaces the synchronous useRegimeAttribution for PortfolioRegimePanel.
// The synchronous endpoint (GET /api/runs/{run_id}/regime-attribution)
// remains in the codebase and is unchanged — do not remove it.
//
// The old useRegimeAttributionParallel hook (TD-FEP-REGIME-ASYNC reference)
// is superseded by this file. That hook can now be deleted.

import { useMutation, useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RegimeAttributionJobStatusResponse =
  components['schemas']['RegimeAttributionJobStatusResponse']
type RegimeAttributionResponse =
  components['schemas']['RegimeAttributionResponse']

// Step 1: Launch the async job
export function useRegimeAttributionCompute() {
  return useMutation({
    mutationFn: (request: {
      run_id: string
      asset: string
      n_contracts?: number
    }): Promise<{ job_id: string; status: string }> =>
      client.post('/api/regime-attribution/compute', request),
  })
}

// Step 2: Poll job status until complete or failed
export function useRegimeAttributionJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: qk.regimeAttributionJob.status(jobId!),
    queryFn: (): Promise<RegimeAttributionJobStatusResponse> =>
      client.get(`/api/regime-attribution/${jobId}/status`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s !== 'complete' && s !== 'failed' ? 2000 : false
    },
    staleTime: 0,
  })
}

// Step 3: Fetch result once status === 'complete'
export function useRegimeAttributionJobResult(
  jobId: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: qk.regimeAttributionJob.result(jobId!),
    queryFn: (): Promise<RegimeAttributionResponse> =>
      client.get(`/api/regime-attribution/${jobId}/result`),
    enabled: !!jobId && enabled,
    staleTime: Infinity,
  })
}
