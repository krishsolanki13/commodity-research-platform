import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'
import type { RunFilters } from '@/api/queryKeys'

type RunListResponse = components['schemas']['RunListResponse']

export function useRuns(filters: RunFilters = {}) {
  const qs = new URLSearchParams()
  if (filters.asset) qs.set('asset', filters.asset)
  if (filters.strategy) qs.set('strategy', filters.strategy)
  if (filters.sort) qs.set('sort', filters.sort)
  if (filters.order) qs.set('order', filters.order)
  if (filters.q) qs.set('q', filters.q)
  if (filters.page) qs.set('page', String(filters.page))
  if (filters.page_size) qs.set('page_size', String(filters.page_size))
  const qsStr = qs.toString()

  return useQuery({
    queryKey: qk.runs(filters),
    queryFn: () => client.get<RunListResponse>(`/api/runs${qsStr ? `?${qsStr}` : ''}`),
    staleTime: 30 * 1000,
    gcTime: 60 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}
