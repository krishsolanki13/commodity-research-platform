import { AlertTriangle } from 'lucide-react'
import { createColumnHelper } from '@tanstack/react-table'
import { DataGrid } from '@/components/data/DataGrid'
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

const colHelper = createColumnHelper<TradeRecord>()

const DIRECTION_OPTIONS: Array<'all' | 'long' | 'short'> = ['all', 'long', 'short']

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
  const columns = [
    colHelper.display({
      id: 'row_num',
      header: '#',
      cell: (info) => info.row.index + 1 + (page - 1) * pageSize,
      size: 48,
    }),
    colHelper.accessor('direction', {
      header: 'DIRECTION',
      size: 90,
      cell: (info) => {
        const value = info.getValue()
        const color = tone.pnl(value === 'long' ? 1 : -1)
        return (
          <span style={{ color }} className="font-mono text-xs">
            {value}
          </span>
        )
      },
    }),
    colHelper.accessor('entry_date', {
      header: 'ENTRY',
      size: 110,
      cell: (info) => <span className="font-mono">{fmt.isoDate(info.getValue())}</span>,
    }),
    colHelper.accessor('exit_date', {
      header: 'EXIT',
      size: 110,
      cell: (info) => <span className="font-mono">{fmt.isoDate(info.getValue())}</span>,
    }),
    colHelper.accessor('duration_bars', {
      header: 'DURATION',
      size: 90,
      cell: (info) => <span className="font-mono">{fmt.tradeBars(info.getValue())}</span>,
    }),
    colHelper.accessor('entry_price', {
      header: 'ENTRY PX',
      size: 100,
      cell: (info) => <span className="font-mono">{fmt.price(info.getValue(), '')}</span>,
    }),
    colHelper.accessor('exit_price', {
      header: 'EXIT PX',
      size: 100,
      cell: (info) => <span className="font-mono">{fmt.price(info.getValue(), '')}</span>,
    }),
    colHelper.accessor('gross_pnl', {
      header: 'GROSS P&L',
      size: 110,
      cell: (info) => {
        const value = info.getValue()
        return (
          <span style={{ color: tone.pnl(value) }} className="font-mono">
            {fmt.compactUsd(value)}
          </span>
        )
      },
    }),
    colHelper.accessor('cost', {
      header: 'COST',
      size: 90,
      cell: (info) => (
        <span className="font-mono text-text-secondary">{fmt.compactUsd(info.getValue())}</span>
      ),
    }),
    colHelper.accessor('net_pnl', {
      header: 'NET P&L',
      size: 100,
      cell: (info) => {
        const value = info.getValue()
        return (
          <span style={{ color: tone.pnl(value) }} className="font-mono font-bold">
            {fmt.compactUsd(value)}
          </span>
        )
      },
    }),
    colHelper.accessor('return_pct', {
      header: 'RETURN',
      size: 90,
      cell: (info) => {
        const value = info.getValue()
        return (
          <span style={{ color: tone.pnl(value) }} className="font-mono">
            {fmt.percent(value)}
          </span>
        )
      },
    }),
    colHelper.display({
      id: 'force_closed',
      header: '⚠',
      size: 40,
      cell: (info) =>
        info.row.original.force_closed ? (
          <span data-testid="force-closed-icon" title="Force-closed at period end">
            <AlertTriangle size={12} className="text-warn" />
          </span>
        ) : null,
    }),
  ]

  return (
    <div className={cn('flex flex-col gap-4', className)}>
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

      <DataGrid<TradeRecord>
        columns={columns}
        data={trades}
        getRowId={(r) =>
          [r.entry_date, r.exit_date, r.direction, r.entry_price, r.exit_price, r.net_pnl].join('|')
        }
        serverPage={{ page, pageSize, total, onPage }}
        virtualized={false}
        toolbar={false as never}
        loading={loading}
        emptyState={{
          title: 'No trades',
          body: 'This strategy generated no trades in the evaluation period.',
        }}
      />
    </div>
  )
}
