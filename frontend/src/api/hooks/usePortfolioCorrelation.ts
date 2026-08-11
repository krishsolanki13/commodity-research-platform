import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { fetchWithRaceRetry } from '@/lib/retry'
import type { components } from '@/api/schema'

type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']

export function usePortfolioCorrelation(runId: string) {
  return useQuery({
    queryKey: qk.portfolioCorrelation(runId),
    queryFn: () =>
      fetchWithRaceRetry(() =>
        client.get<CorrelationReportResponse>(
          `/api/portfolio/${runId}/correlation`,
        ),
      ),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
    retry: false,
  })
}
