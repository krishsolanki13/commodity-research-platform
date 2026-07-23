import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'

interface DeleteResponse {
  deleted: boolean
  run_id: string
}

export function usePortfolioDelete() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => client.delete<DeleteResponse>(`/api/portfolio/${runId}`),
    onSuccess: (_data, runId) => {
      queryClient.removeQueries({ queryKey: ['portfolio', runId] })
      void queryClient.invalidateQueries({ queryKey: qk.portfolioRuns() })
    },
  })
}
