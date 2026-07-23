import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type TradesPageResponse = components['schemas']['TradesPageResponse']

/** Build query params for GET /api/runs/{id}/trades — server-side filters only. */
export function buildTradeQueryParams(
  page: number,
  direction?: 'long' | 'short',
  forceClosed?: boolean
): URLSearchParams {
  const params = new URLSearchParams({ page: String(page), page_size: '100' })
  if (direction) params.set('direction', direction)
  if (forceClosed !== undefined) params.set('force_closed', String(forceClosed))
  return params
}

export function useRunTrades(
  runId: string,
  page = 1,
  direction?: 'long' | 'short',
  forceClosed?: boolean
) {
  const filters = {
    ...(direction !== undefined && { direction }),
    ...(forceClosed !== undefined && { forceClosed }),
  }

  const qs = buildTradeQueryParams(page, direction, forceClosed)

  return useQuery({
    queryKey: qk.runTrades(runId, page, filters),
    queryFn: () => client.get<TradesPageResponse>(`/api/runs/${runId}/trades?${qs}`),
    enabled: !!runId,
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
