import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RollingICResponse = components['schemas']['RollingICResponse']

export function useRollingIC(
  asset: string | null,
  strategy: string | null,
  params: Record<string, unknown> | null,
  window: number = 63,
) {
  const paramsKey = JSON.stringify(params ?? {})
  const qs = new URLSearchParams({
    asset: asset ?? '',
    strategy: strategy ?? '',
    params: paramsKey,
    window: String(window),
  })
  return useQuery({
    queryKey: qk.rollingIc(asset!, strategy!, paramsKey, window),
    queryFn: (): Promise<RollingICResponse> =>
      client.get(`/api/signals/rolling-ic?${qs}`),
    enabled: !!asset && !!strategy && !!params,
    staleTime: Infinity,
  })
}
