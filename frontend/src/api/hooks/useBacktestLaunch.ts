import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type BacktestLaunchRequest = components['schemas']['BacktestLaunchRequest']
type TaskLaunchResponse = components['schemas']['TaskLaunchResponse']

export function useBacktestLaunch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: BacktestLaunchRequest) =>
      client.post<TaskLaunchResponse>('/api/backtests', request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.runs({}) })
    },
  })
}
