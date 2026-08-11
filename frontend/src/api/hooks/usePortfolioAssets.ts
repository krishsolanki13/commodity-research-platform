import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { fetchWithRaceRetry } from '@/lib/retry'
import type { components } from '@/api/schema'

type PortfolioAssetsResponse = components['schemas']['PortfolioAssetsResponse']

export function usePortfolioAssets(runId: string) {
  return useQuery({
    queryKey: qk.portfolioAssets(runId),
    queryFn: () =>
      fetchWithRaceRetry(() =>
        client.get<PortfolioAssetsResponse>(`/api/portfolio/${runId}/assets`),
      ),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
    retry: false,
  })
}
