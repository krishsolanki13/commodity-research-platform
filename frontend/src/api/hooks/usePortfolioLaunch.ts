import { useMutation } from '@tanstack/react-query'
import { client } from '@/api/client'
import type { components } from '@/api/schema'

type PortfolioLaunchRequest = components['schemas']['PortfolioLaunchRequest']
type TaskLaunchResponse = components['schemas']['TaskLaunchResponse']

export function usePortfolioLaunch() {
  return useMutation({
    mutationFn: (request: PortfolioLaunchRequest) =>
      client.post<TaskLaunchResponse>('/api/portfolio/run', request),
    onSuccess: () => {
      // No run list to invalidate in F12
    },
  })
}
