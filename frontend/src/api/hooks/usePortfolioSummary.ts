import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

export function usePortfolioSummary(runId: string) {
  return useQuery({
    queryKey: qk.portfolioSummary(runId),
    queryFn: () => client.get<PortfolioSummaryResponse>(`/api/portfolio/${runId}/summary`),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
  })
}
