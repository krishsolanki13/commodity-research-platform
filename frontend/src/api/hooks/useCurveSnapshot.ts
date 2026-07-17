import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

// VERIFY type name before use:
//   grep -n "FuturesCurve\|CurveSnapshot\|CurveResponse" src/api/schema.d.ts
// Update the alias below if the actual schema name differs.
type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']

export function useCurveSnapshot(asset: string, nContracts = 6) {
  return useQuery({
    queryKey: qk.curveSnapshot(asset, nContracts),
    queryFn: () =>
      client.get<FuturesCurveResponse>(
        `/api/curves/${asset}/snapshot?n_contracts=${nContracts}`
      ),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled: !!asset,
  })
}
