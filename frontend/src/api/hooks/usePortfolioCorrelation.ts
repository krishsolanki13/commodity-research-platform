import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']

export function usePortfolioCorrelation(runId: string) {
  return useQuery({
    queryKey: qk.portfolioCorrelation(runId),
    queryFn: () =>
      client.get<CorrelationReportResponse>(
        `/api/portfolio/${runId}/correlation`
      ),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
  })
}
