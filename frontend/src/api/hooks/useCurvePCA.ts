import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type CurvePCAResponse = components['schemas']['CurvePCAResponse']

export function useCurvePCA(
  asset: string | null,
  nComponents: number = 3,
  nContracts: number = 4,
  fromDate?: string,
  toDate?: string,
) {
  const qs = new URLSearchParams({
    asset: asset ?? '',
    n_components: String(nComponents),
    n_contracts: String(nContracts),
  })
  if (fromDate) qs.set('from_date', fromDate)
  if (toDate) qs.set('to_date', toDate)

  return useQuery({
    queryKey: qk.curvePca(asset!, nComponents, nContracts, fromDate, toDate),
    queryFn: (): Promise<CurvePCAResponse> =>
      client.get(`/api/intelligence/pca?${qs}`),
    enabled: !!asset,
    staleTime: 10 * 60 * 1000,
  })
}
