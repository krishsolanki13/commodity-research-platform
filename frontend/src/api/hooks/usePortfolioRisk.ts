import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RiskReportResponse = components['schemas']['RiskReportResponse']

export function usePortfolioRisk(runId: string) {
  return useQuery({
    queryKey: qk.portfolioRisk(runId),
    queryFn: () => client.get<RiskReportResponse>(`/api/portfolio/${runId}/risk`),
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    enabled: !!runId,
  })
}
