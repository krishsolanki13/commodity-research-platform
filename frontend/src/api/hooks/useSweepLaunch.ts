import { useMutation } from '@tanstack/react-query'
import { client } from '@/api/client'
import type { components } from '@/api/schema'

type SweepLaunchRequest = components['schemas']['SweepLaunchRequest']
// Launch returns SweepStatusResponse (no SweepLaunchResponse in schema)
type SweepStatusResponse = components['schemas']['SweepStatusResponse']

export function useSweepLaunch() {
  return useMutation({
    mutationFn: (request: SweepLaunchRequest): Promise<SweepStatusResponse> =>
      client.post('/api/sweeps', request),
  })
}
