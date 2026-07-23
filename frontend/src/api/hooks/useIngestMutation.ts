import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type IngestRequest = components['schemas']['IngestRequest']
type IngestResponse = components['schemas']['IngestResponse']

/**
 * POST /api/system/ingest — trigger universe (or single-asset) re-ingestion.
 * Pass `{ asset: null }` for all assets. 202 means accepted, not complete.
 */
export function useIngestMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: IngestRequest) =>
      client.post<IngestResponse>('/api/system/ingest', request),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: qk.assets() })
      void queryClient.invalidateQueries({ queryKey: qk.dataStatus() })
      if (variables.asset) {
        void queryClient.invalidateQueries({ queryKey: qk.assetSummary(variables.asset) })
        void queryClient.invalidateQueries({ queryKey: qk.assetOhlcv(variables.asset) })
      }
    },
  })
}
