import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

export function useRegimeAttribution(runId: string | null, nContracts: number = 4) {
  const qs = new URLSearchParams({ n_contracts: String(nContracts) })
  return useQuery({
    queryKey: qk.regimeAttribution(runId!, nContracts),
    queryFn: (): Promise<RegimeAttributionResponse> =>
      client.get(`/api/runs/${runId}/regime-attribution?${qs}`),
    enabled: !!runId,
    staleTime: Infinity,
  })
}
