import { useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type TradesPageResponse = components['schemas']['TradesPageResponse']

/**
 * Paginated trades fetch. When pageSize >= 500 and no server filters are set,
 * fetches every page and merges — needed because client-side direction filters
 * must see the full trade set (backend ?direction= filter is broken for int64
 * parquet values).
 */
export function useRunTrades(
  runId: string,
  page = 1,
  direction?: 'long' | 'short',
  forceClosed?: boolean,
  pageSize = 100
) {
  const filters = {
    ...(direction !== undefined && { direction }),
    ...(forceClosed !== undefined && { forceClosed }),
    pageSize,
  }

  const fetchAll = pageSize >= 500 && direction === undefined && forceClosed === undefined

  return useQuery({
    queryKey: qk.runTrades(runId, fetchAll ? 0 : page, filters),
    queryFn: async (): Promise<TradesPageResponse> => {
      if (!fetchAll) {
        const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
        if (direction) qs.set('direction', direction)
        if (forceClosed !== undefined) qs.set('force_closed', String(forceClosed))
        return client.get<TradesPageResponse>(`/api/runs/${runId}/trades?${qs}`)
      }

      const maxPage = 500
      let pageNum = 1
      let trades: TradesPageResponse['trades'] = []
      let total = Infinity
      let stats: TradesPageResponse['stats'] | undefined
      let run_id = runId

      while (trades.length < total) {
        const qs = new URLSearchParams({ page: String(pageNum), page_size: String(maxPage) })
        const res = await client.get<TradesPageResponse>(`/api/runs/${runId}/trades?${qs}`)
        run_id = res.run_id
        stats = res.stats
        total = res.total
        trades = trades.concat(res.trades)
        if (res.trades.length === 0) break
        pageNum += 1
      }

      return {
        run_id,
        trades,
        page: 1,
        page_size: trades.length,
        total: trades.length,
        stats: stats ?? {
          n_trades: trades.length,
          avg_duration_bars: null,
          avg_win: null,
          avg_loss: null,
          largest_win: null,
          largest_loss: null,
        },
      }
    },
    enabled: !!runId,
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
  })
}
