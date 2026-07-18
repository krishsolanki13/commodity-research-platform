import { useQueries } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']

export interface AssetSnapshotWithLabel {
  asset: string
  label: string
  snapshot: FuturesCurveResponse
}

export function useCurveSnapshots(assets: string[], nContracts = 4) {
  return useQueries({
    queries: assets.map((asset) => ({
      queryKey: qk.curveSnapshot(asset, nContracts, undefined),
      queryFn: () =>
        client.get<FuturesCurveResponse>(`/api/curves/${asset}/snapshot?n_contracts=${nContracts}`),
      staleTime: 5 * 60 * 1000,
      gcTime: 60 * 60 * 1000,
      enabled: !!asset,
    })),
  })
}
