import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type SignalGenerateResponse = components['schemas']['SignalGenerateResponse']

export function useSignalGenerate(
  asset: string,
  strategy: string,
  params: Record<string, unknown> | null
) {
  return useQuery({
    queryKey: qk.signalGenerate(asset, strategy, params),
    queryFn: () =>
      client.post<SignalGenerateResponse>('/api/signals/generate', {
        asset,
        strategy,
        params,
      }),
    staleTime: Infinity,
    enabled: false, // CRITICAL: never auto-fetches — evaluate chain uses setQueryData
    gcTime: 60 * 60 * 1000,
  })
}
