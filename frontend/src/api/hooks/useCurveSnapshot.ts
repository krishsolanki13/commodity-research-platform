import { useQuery } from '@tanstack/react-query'
import { client, ApiClientError } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

// VERIFY type name before use:
//   grep -n "FuturesCurve\|CurveSnapshot\|CurveResponse" src/api/schema.d.ts
// Update the alias below if the actual schema name differs.
type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']

export function useCurveSnapshot(
  asset: string,
  nContracts = 6,
  observationDate?: string
) {
  const qs = new URLSearchParams({ n_contracts: String(nContracts) })
  if (observationDate) qs.set('observation_date', observationDate)

  return useQuery({
    queryKey: qk.curveSnapshot(asset, nContracts, observationDate),
    queryFn: () =>
      client.get<FuturesCurveResponse>(`/api/curves/${asset}/snapshot?${qs}`),
    staleTime: observationDate ? Infinity : 5 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    enabled: !!asset,
    retry: (failureCount, error) => {
      if (
        error instanceof ApiClientError &&
        (error.apiError.status === 404 || error.apiError.status === 422)
      )
        return false
      return failureCount < 1
    },
  })
}
