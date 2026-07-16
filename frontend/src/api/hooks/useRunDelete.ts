import { useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type DeleteResponse = components['schemas']['DeleteResponse']

export function useRunDelete() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (runId: string) => client.delete<DeleteResponse>(`/api/runs/${runId}`),
    onSuccess: (_data, runId) => {
      void queryClient.invalidateQueries({ queryKey: ['runs'] })
      queryClient.removeQueries({ queryKey: qk.run(runId) })
      queryClient.removeQueries({ queryKey: ['runs', runId] })
    },
  })
}
