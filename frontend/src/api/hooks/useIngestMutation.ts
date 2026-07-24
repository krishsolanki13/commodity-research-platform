import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type IngestRequest = components['schemas']['IngestRequest']
type IngestResponse = components['schemas']['IngestResponse']
type UniverseResponse = components['schemas']['UniverseResponse']

/**
 * POST /api/system/ingest — trigger universe (or single-asset) re-ingestion.
 * Pass `{ asset: null }` for all assets. 202 means accepted, not complete.
 */
export function useIngestMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: IngestRequest) =>
      client.post<IngestResponse>('/api/system/ingest', request),
    onSuccess: async (_data, variables) => {
      // Exact keys from qk / useDataStatus + useAssets (Step 1d)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: qk.dataStatus() }),
        queryClient.invalidateQueries({ queryKey: qk.assets() }),
      ])
      // /api/assets currently returns last_ingestion: null — stamp ingest time so
      // the Market Overview LAST INGESTION metric updates without a full page reload.
      const ingestedAt = new Date().toISOString()
      queryClient.setQueryData(qk.assets(), (old: UniverseResponse | undefined) =>
        old ? { ...old, last_ingestion: ingestedAt } : old
      )
      if (variables.asset) {
        void queryClient.invalidateQueries({ queryKey: qk.assetSummary(variables.asset) })
        void queryClient.invalidateQueries({ queryKey: qk.assetOhlcv(variables.asset) })
      }
    },
  })
}
