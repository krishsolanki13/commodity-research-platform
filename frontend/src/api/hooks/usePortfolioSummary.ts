import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { fetchWithRaceRetry } from '@/lib/retry'
import type { components } from '@/api/schema'

type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

export function usePortfolioSummary(runId: string) {
  return useQuery({
    queryKey: qk.portfolioSummary(runId),
    queryFn: () =>
      fetchWithRaceRetry(() =>
        client.get<PortfolioSummaryResponse>(`/api/portfolio/${runId}/summary`),
      ),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
    retry: false,
  })
}
