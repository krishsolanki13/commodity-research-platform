import { AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react'
import { MetricStat } from '@/components/data/MetricStat'
import { fmt } from '@/lib/fmt'
import { tone } from '@/lib/tone'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type TradeRecord = components['schemas']['TradeRecord']
type TradeStats = components['schemas']['TradeStats']

interface TradeTableProps {
  runId: string
  trades: TradeRecord[]
  page: number
  pageSize: number
  total: number
  stats: TradeStats
  onPage: (page: number) => void
  direction: 'all' | 'long' | 'short'
  onDirectionChange: (direction: 'all' | 'long' | 'short') => void
  forceClosed: boolean | null
  onForceClosedChange: (value: boolean | null) => void
  loading?: boolean
  className?: string
}

const DIRECTION_OPTIONS: Array<'all' | 'long' | 'short'> = ['all', 'long', 'short']

const COLUMNS = ['#', 'DIRECTION', 'ENTRY', 'EXIT', 'DURATION', 'ENTRY PX', 'EXIT PX', 'GROSS P&L', 'COST', 'NET P&L', 'RETURN', '?']
const COL_WIDTHS = [48, 90, 110, 110, 90, 100, 100, 110, 90, 100, 90, 40]

export function TradeTable({
  runId: _runId,
  trades,
  page,
  pageSize,
  total,
  stats,
  onPage,
  direction,
  onDirectionChange,
  forceClosed,
  onForceClosedChange,
  loading,
  className,
}: TradeTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className={cn('flex w-full flex-col gap-4', className)}>
      <div className="flex items-center gap-4">
        <div className="flex overflow-hidden rounded-sm border border-border-strong">
          {DIRECTION_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => onDirectionChange(opt)}
              aria-pressed={direction === opt}
              className={cn(
                'border-r border-border-strong px-2 py-1 font-mono text-xs capitalize last:border-r-0',
                'transition-colors duration-fast',
                direction === opt
                  ? 'bg-bg-selected font-medium text-text-primary'
                  : 'bg-bg-app text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              )}
            >
              {opt}
            </button>
          ))}
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-text-secondary">
          <input
            type="checkbox"
            checked={forceClosed === true}
            onChange={(e) => onForceClosedChange(e.target.checked ? true : null)}
            className="cursor-pointer"
          />
          Force-closed only
        </label>
      </div>

      <div className="grid grid-cols-6 gap-4">
        <MetricStat label="N TRADES" value={stats.n_trades} format="integer" tone="neutral" />
        <MetricStat
          label="AVG DURATION"
          value={stats.avg_duration_bars}
          format="bars"
          tone="neutral"
        />
        <MetricStat label="AVG WIN" value={stats.avg_win} format="compactUsd" />
        <MetricStat label="AVG LOSS" value={stats.avg_loss} format="compactUsd" />
        <MetricStat label="LARGEST WIN" value={stats.largest_win} format="compactUsd" />
        <MetricStat label="LARGEST LOSS" value={stats.largest_loss} format="compactUsd" />
      </div>

      {trades.length === 0 && !loading ? (
        <div className="flex h-32 flex-col items-center justify-center gap-1 text-center text-sm text-text-secondary">
          <span className="font-medium">No trades</span>
          <span className="text-xs text-text-disabled">
            This strategy generated no trades in the evaluation period.
          </span>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="overflow-hidden rounded border border-border-default">
          <table className="w-full table-fixed border-collapse text-sm">
            <colgroup>
              {COL_WIDTHS.map((w, i) => (
                <col key={i} style={{ width: w }} />
              ))}
            </colgroup>
            <thead className="bg-bg-raised">
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col}
                    scope="col"
                    className="px-2 py-2 text-left text-xs font-medium text-text-secondary"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="py-8 text-center text-xs text-text-disabled">
                    Loading.
                  </td>
                </tr>
              ) : (
                trades.map((trade, idx) => {
                  const rowNum = idx + 1 + (page - 1) * pageSize
                  return (
                    <tr
                      key={[
                        trade.entry_date,
                        trade.exit_date,
                        trade.direction,
                        trade.entry_price,
                        trade.exit_price,
                        trade.net_pnl,
                      ].join('|')}
                      className="border-b border-border-subtle"
                    >
                      <td className="px-2 py-1.5 font-mono text-xs text-text-secondary">{rowNum}</td>
                      <td className="px-2 py-1.5">
                        <span
                          style={{ color: tone.pnl(trade.direction === 'long' ? 1 : -1) }}
                          className="font-mono text-xs"
                        >
                          {trade.direction}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 font-mono">{fmt.isoDate(trade.entry_date)}</td>
                      <td className="px-2 py-1.5 font-mono">{fmt.isoDate(trade.exit_date)}</td>
                      <td className="px-2 py-1.5 font-mono">{fmt.tradeBars(trade.duration_bars)}</td>
                      <td className="px-2 py-1.5 font-mono">{fmt.price(trade.entry_price, '')}</td>
                      <td className="px-2 py-1.5 font-mono">{fmt.price(trade.exit_price, '')}</td>
                      <td className="px-2 py-1.5">
                        <span style={{ color: tone.pnl(trade.gross_pnl) }} className="font-mono">
                          {fmt.compactUsd(trade.gross_pnl)}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        <span className="font-mono text-text-secondary">
                          {fmt.compactUsd(trade.cost)}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        <span style={{ color: tone.pnl(trade.net_pnl) }} className="font-mono font-bold">
                          {fmt.compactUsd(trade.net_pnl)}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        <span style={{ color: tone.pnl(trade.return_pct) }} className="font-mono">
                          {fmt.percent(trade.return_pct)}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        {trade.force_closed ? (
                          <span data-testid="force-closed-icon" title="Force-closed at period end">
                            <AlertTriangle size={12} className="text-warn" />
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-text-secondary">
          <span>
            {total} trade{total !== 1 ? 's' : ''} · page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPage(page - 1)}
              className="rounded p-1 hover:bg-bg-hover disabled:opacity-40"
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPage(page + 1)}
              className="rounded p-1 hover:bg-bg-hover disabled:opacity-40"
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
