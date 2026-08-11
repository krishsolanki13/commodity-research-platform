import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { fetchWithRaceRetry } from '@/lib/retry'
import type { components } from '@/api/schema'

type PortfolioEquityResponse = components['schemas']['PortfolioEquityResponse']

export function usePortfolioEquity(runId: string) {
  return useQuery({
    queryKey: qk.portfolioEquity(runId),
    queryFn: () =>
      fetchWithRaceRetry(() =>
        client.get<PortfolioEquityResponse>(`/api/portfolio/${runId}/equity`),
      ),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
    retry: false,
  })
}
