import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type QCReportResponse = components['schemas']['QCReportResponse']

export function useDataQC(asset: string | null) {
  const qs = new URLSearchParams({ asset: asset ?? '' })
  return useQuery({
    queryKey: qk.dataQc(asset!),
    queryFn: (): Promise<QCReportResponse> => client.get(`/api/system/data/qc?${qs}`),
    enabled: !!asset,
    staleTime: 10 * 60 * 1000,
  })
}
