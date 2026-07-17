import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

// VERIFY type name before use:
//   grep -n "CurveAvailable\|AvailableAssets" src/api/schema.d.ts
// Update the alias below if the actual schema name differs.
type CurveAvailableResponse = components['schemas']['CurveAvailableResponse']

export function useCurveAvailableAssets() {
  return useQuery({
    queryKey: qk.curveAvailable(),
    queryFn: () => client.get<CurveAvailableResponse>('/api/curves/available'),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
