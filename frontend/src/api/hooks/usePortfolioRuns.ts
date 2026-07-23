import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type PortfolioRunListResponse = components['schemas']['PortfolioRunListResponse']

export function usePortfolioRuns() {
  return useQuery({
    queryKey: qk.portfolioRuns(),
    queryFn: () => client.get<PortfolioRunListResponse>('/api/portfolio/runs'),
    staleTime: Infinity, // run list is append-only; immutable once written
  })
}
