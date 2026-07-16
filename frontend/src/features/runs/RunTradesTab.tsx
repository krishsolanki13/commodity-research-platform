/**
 * RunTradesTab — paginated trade log with direction/forceClosed filters.
 * Filters are component state — NOT in URL (tab is already URL-synced).
 */
import { useState } from 'react'
import { useRunTrades } from '@/api/hooks'
import { TradeTable } from '@/components/data/TradeTable'
import type { components } from '@/api/schema'

type TradeStats = components['schemas']['TradeStats']

const DEFAULT_STATS: TradeStats = {
  n_trades: 0,
  avg_duration_bars: 0,
  avg_win: 0,
  avg_loss: 0,
  largest_win: 0,
  largest_loss: 0,
}

interface RunTradesTabProps {
  runId: string
}

export function RunTradesTab({ runId }: RunTradesTabProps) {
  const [page, setPage] = useState(1)
  const [direction, setDirection] = useState<'all' | 'long' | 'short'>('all')
  const [forceClosed, setForceClosed] = useState<boolean | null>(null)

  const tradesQuery = useRunTrades(
    runId,
    page,
    direction !== 'all' ? direction : undefined,
    forceClosed ?? undefined
  )

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
      trades={tradesQuery.data?.trades ?? []}
      page={page}
      pageSize={tradesQuery.data?.page_size ?? 100}
      total={tradesQuery.data?.total ?? 0}
      stats={tradesQuery.data?.stats ?? DEFAULT_STATS}
      onPage={setPage}
      direction={direction}
      onDirectionChange={handleDirectionChange}
      forceClosed={forceClosed}
      onForceClosedChange={handleForceClosedChange}
      loading={tradesQuery.isLoading}
    />
  )
}
