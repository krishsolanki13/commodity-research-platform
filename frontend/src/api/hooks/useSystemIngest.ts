import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type IngestRequest = components['schemas']['IngestRequest']
type IngestResponse = components['schemas']['IngestResponse']

/**
 * POST /api/system/ingest — trigger universe (or single-asset) re-ingestion.
 * Pass `null` for all assets. 202 means accepted, not complete.
 */
export function useSystemIngest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (asset: string | null = null) =>
      client.post<IngestResponse>('/api/system/ingest', { asset } satisfies IngestRequest),
    onSuccess: (_data, asset) => {
      void queryClient.invalidateQueries({ queryKey: qk.assets() })
      void queryClient.invalidateQueries({ queryKey: qk.dataStatus() })
      if (asset) {
        void queryClient.invalidateQueries({ queryKey: qk.assetSummary(asset) })
        void queryClient.invalidateQueries({ queryKey: qk.assetOhlcv(asset) })
      }
    },
  })
}
