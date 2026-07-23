import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type PortfolioLaunchRequest = components['schemas']['PortfolioLaunchRequest']
type TaskLaunchResponse = components['schemas']['TaskLaunchResponse']

export function usePortfolioLaunch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (request: PortfolioLaunchRequest) =>
      client.post<TaskLaunchResponse>('/api/portfolio/run', request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.portfolioRuns() })
    },
  })
}
