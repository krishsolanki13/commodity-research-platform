import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type ValidationStatusResponse = components['schemas']['ValidationStatusResponse']

export function useValidationStatus(id: string | null) {
  return useQuery({
    queryKey: qk.validation.status(id!),
    queryFn: (): Promise<ValidationStatusResponse> =>
      client.get(`/api/validation/${id}/status`),
    enabled: !!id,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s !== 'complete' && s !== 'failed' ? 2000 : false
    },
    staleTime: 0,
  })
}
