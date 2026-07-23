/**
 * RunTradesTab — paginated trade log with direction/forceClosed filters.
 * Filters are component state — NOT in URL (tab is already URL-synced).
 * Filtering is server-side via ?direction= and ?force_closed= query params.
 *
 * KPI stats are recomputed from the filtered trade page so Avg Duration /
 * Avg Win / Avg Loss update when the direction filter changes (backend
 * currently returns unfiltered metric-file averages alongside filtered rows).
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

function computeFilteredStats(trades: TradeRecord[], total: number): TradeStats {
  const nTrades = total
  if (trades.length === 0) {
    return {
      n_trades: nTrades,
      avg_duration_bars: 0,
      avg_win: 0,
      avg_loss: 0,
      largest_win: 0,
      largest_loss: 0,
    }
  }

  const avgDuration = Math.round(
    trades.reduce((sum, t) => sum + t.duration_bars, 0) / trades.length
  )

  const wins = trades.filter((t) => t.net_pnl > 0)
  const losses = trades.filter((t) => t.net_pnl < 0)

  const avgWin =
    wins.length > 0 ? wins.reduce((sum, t) => sum + t.net_pnl, 0) / wins.length : 0
  const avgLoss =
    losses.length > 0 ? losses.reduce((sum, t) => sum + t.net_pnl, 0) / losses.length : 0
  const largestWin = wins.length > 0 ? Math.max(...wins.map((t) => t.net_pnl)) : 0
  const largestLoss = losses.length > 0 ? Math.min(...losses.map((t) => t.net_pnl)) : 0

  return {
    n_trades: nTrades,
    avg_duration_bars: avgDuration,
    avg_win: avgWin,
    avg_loss: avgLoss,
    largest_win: largestWin,
    largest_loss: largestLoss,
  }
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

  const filteredTrades = tradesQuery.data?.trades ?? []
  const total = tradesQuery.data?.total ?? filteredTrades.length

  const stats = useMemo(
    () =>
      tradesQuery.data
        ? computeFilteredStats(filteredTrades, total)
        : DEFAULT_STATS,
    [filteredTrades, total, tradesQuery.data]
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
      trades={filteredTrades}
      page={page}
      pageSize={tradesQuery.data?.page_size ?? 100}
      total={total}
      stats={stats}
      onPage={setPage}
      direction={direction}
      onDirectionChange={handleDirectionChange}
      forceClosed={forceClosed}
      onForceClosedChange={handleForceClosedChange}
      loading={tradesQuery.isLoading}
    />
  )
}
