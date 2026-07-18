import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type TaskStatusResponse = components['schemas']['TaskStatusResponse']

export function usePortfolioStatus(runId: string | null) {
  return useQuery({
    queryKey: qk.portfolioStatus(runId ?? ''),
    queryFn: () => client.get<TaskStatusResponse>(`/api/portfolio/${runId}/status`),
    enabled: !!runId,
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'complete' || status === 'failed') return false
      return 1000
    },
    retry: 0,
  })
}
