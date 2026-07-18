import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type PortfolioAssetsResponse = components['schemas']['PortfolioAssetsResponse']

export function usePortfolioAssets(runId: string) {
  return useQuery({
    queryKey: qk.portfolioAssets(runId),
    queryFn: () =>
      client.get<PortfolioAssetsResponse>(`/api/portfolio/${runId}/assets`),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
  })
}
