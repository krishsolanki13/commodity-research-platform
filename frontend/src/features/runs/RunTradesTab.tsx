/**
 * RunTradesTab — paginated trade log with direction/forceClosed filters.
 * Filters are component state — NOT in URL (tab is already URL-synced).
 *
 * Filtering is client-side: the API returns direction as 'long'/'short', but
 * parquet stores int64 1/-1, so server-side ?direction=long returns 0 rows.
 */
import { useMemo, useState } from 'react'
import { useRunTrades } from '@/api/hooks'
import { TradeTable } from '@/components/data/TradeTable'
import type { components } from '@/api/schema'

type TradeStats = components['schemas']['TradeStats']
type TradeRecord = components['schemas']['TradeRecord']

const DEFAULT_STATS: TradeStats = {
  n_trades: 0,
  avg_duration_bars: 0,
  avg_win: 0,
  avg_loss: 0,
  largest_win: 0,
  largest_loss: 0,
}

const PAGE_SIZE = 100

interface RunTradesTabProps {
  runId: string
}

export function RunTradesTab({ runId }: RunTradesTabProps) {
  const [page, setPage] = useState(1)
  const [direction, setDirection] = useState<'all' | 'long' | 'short'>('all')
  const [forceClosed, setForceClosed] = useState<boolean | null>(null)

  // Fetch unfiltered — backend direction filter is broken for int64 parquet values.
  // page_size=500 is the API max; client-side filter + paginate below.
  const tradesQuery = useRunTrades(runId, 1, undefined, undefined, 500)

  const filteredTrades = useMemo(() => {
    const allTrades = tradesQuery.data?.trades ?? []
    return allTrades.filter((trade: TradeRecord) => {
      if (forceClosed === true && trade.force_closed !== true) return false
      if (direction === 'long' && trade.direction !== 'long') return false
      if (direction === 'short' && trade.direction !== 'short') return false
      return true
    })
  }, [tradesQuery.data?.trades, direction, forceClosed])

  const pageTrades = filteredTrades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const displayStats: TradeStats = {
    ...(tradesQuery.data?.stats ?? DEFAULT_STATS),
    n_trades: filteredTrades.length,
  }

  function handleDirectionChange(d: 'all' | 'long' | 'short') {
    setPage(1)
    setDirection(d)
  }

  function handleForceClosedChange(v: boolean | null) {
    setPage(1)
    setForceClosed(v)
  }

  return (
    <TradeTable
      runId={runId}
      trades={pageTrades}
      page={page}
      pageSize={PAGE_SIZE}
      total={filteredTrades.length}
      stats={displayStats}
      onPage={setPage}
      direction={direction}
      onDirectionChange={handleDirectionChange}
      forceClosed={forceClosed}
      onForceClosedChange={handleForceClosedChange}
      loading={tradesQuery.isLoading}
    />
  )
}
