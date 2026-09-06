import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'

// Backend returns an untyped dict (OpenAPI additionalProperties).
export interface CurveCoverageResponse {
  asset: string
  curve_coverage_start: string | null
  message: string
  n_contracts?: number
}

export function useCurveCoverage(asset: string | null, strategy: string | null) {
  return useQuery({
    queryKey: qk.curveCoverage(asset!),
    queryFn: (): Promise<CurveCoverageResponse> =>
      client.get(`/api/system/curve-coverage/${asset}`),
    enabled: !!asset && strategy === 'carry',
    staleTime: 10 * 60 * 1000,
  })
}
