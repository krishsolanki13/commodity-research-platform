import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

// VERIFY type name before use:
//   grep -n "CurveHistory\|HistoryResponse" src/api/schema.d.ts
// Update the alias below if the actual schema name differs.
type CurveHistoryResponse = components['schemas']['CurveHistoryResponse']

export function useCurveHistory(asset: string, fromDate: string, toDate: string, nContracts = 6) {
  const qs = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
    n_contracts: String(nContracts),
  })

  return useQuery({
    queryKey: qk.curveHistory(asset, fromDate, toDate, nContracts),
    queryFn: () => client.get<CurveHistoryResponse>(`/api/curves/${asset}/history?${qs}`),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled: !!asset && !!fromDate && !!toDate,
  })
}
