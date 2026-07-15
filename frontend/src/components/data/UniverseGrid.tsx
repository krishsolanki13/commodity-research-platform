import { createColumnHelper } from '@tanstack/react-table'
import { DataGrid } from '@/components/data/DataGrid'
import { Sparkline } from '@/components/charts/Sparkline'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'
import { fmt } from '@/lib/fmt'
import { tone } from '@/lib/tone'
import { cn } from '@/lib/cn'

export interface AssetRow {
  name: string
  displayName: string
  ticker: string
  exchange: string
  lastPrice: number | null
  lastDate: string | null
  return1d: number | null
  return1w: number | null
  return1m: number | null
  realizedVol63d: number | null
  avgVolume20d: number | null
  barCount: number
  dataHealth: 'ok' | 'warn' | 'crit' | 'missing'
  flaggedAnomalies: number
  sparklineValues: (number | null)[]
}

interface UniverseGridProps {
  rows: AssetRow[]
  onRowClick: (asset: string) => void
  onHoverAsset?: (asset: string) => void // accepted but deferred (TD-F4-HOVER)
  loading?: boolean
  className?: string
}

const colHelper = createColumnHelper<AssetRow>()

// Health dot color map using CSS variable strings (not hex literals)
const healthColorMap: Record<AssetRow['dataHealth'], string> = {
  ok: 'var(--ok-500)',
  warn: 'var(--warn-500)',
  crit: 'var(--crit-500)',
  missing: 'var(--text-disabled)',
}

const columns = [
  colHelper.accessor('displayName', {
    header: 'ASSET',
    cell: (info) => (
      <div className="gap-0.5 flex flex-col">
        <span className="font-medium text-text-emphasis">{info.getValue()}</span>
        <span className="font-mono text-xs text-text-secondary">{info.row.original.ticker}</span>
      </div>
    ),
  }),
  colHelper.accessor('lastPrice', {
    header: 'LAST',
    cell: (info) => {
      const v = info.getValue()
      return v !== null ? (
        <span className="block text-right font-mono">{fmt.price(v, info.row.original.name)}</span>
      ) : (
        <span className="text-text-secondary">â€”</span>
      )
    },
  }),
  colHelper.accessor('return1d', {
    header: '1D%',
    cell: (info) => {
      const v = info.getValue()
      if (v === null) return <span className="text-text-secondary">â€”</span>
      return (
        <span style={{ color: tone.pnl(v) }} className="font-mono">
          {fmt.percent(v)}
        </span>
      )
    },
  }),
  colHelper.accessor('return1w', {
    header: '1W%',
    cell: (info) => {
      const v = info.getValue()
      if (v === null) return <span className="text-text-secondary">â€”</span>
      return (
        <span style={{ color: tone.pnl(v) }} className="font-mono">
          {fmt.percent(v)}
        </span>
      )
    },
  }),
  colHelper.accessor('return1m', {
    header: '1M%',
    cell: (info) => {
      const v = info.getValue()
      if (v === null) return <span className="text-text-secondary">â€”</span>
      return (
        <span style={{ color: tone.pnl(v) }} className="font-mono">
          {fmt.percent(v)}
        </span>
      )
    },
  }),
  colHelper.accessor('realizedVol63d', {
    header: 'VOL 63D',
    cell: (info) => {
      const v = info.getValue()
      if (v === null) return <span className="text-text-secondary">â€”</span>
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="font-mono text-text-primary">
              {fmt.percent(v, { showPlus: false })}
            </span>
          </TooltipTrigger>
          <TooltipContent>63d realized volatility (annualized)</TooltipContent>
        </Tooltip>
      )
    },
  }),
  colHelper.display({
    id: 'sparkline',
    header: '20D',
    enableSorting: false,
    cell: (info) => (
      <Sparkline values={info.row.original.sparklineValues} tone="auto" width={80} height={24} />
    ),
  }),
  colHelper.accessor('dataHealth', {
    header: 'HEALTH',
    enableSorting: false,
    cell: (info) => {
      const health = info.getValue()
      const flags = info.row.original.flaggedAnomalies
      const label =
        health === 'ok'
          ? 'No anomalies'
          : health === 'missing'
            ? 'Not ingested'
            : `${flags} flag${flags !== 1 ? 's' : ''}`
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              aria-label={label}
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: healthColorMap[health] }}
            />
          </TooltipTrigger>
          <TooltipContent>{label}</TooltipContent>
        </Tooltip>
      )
    },
  }),
  colHelper.accessor('lastDate', {
    header: 'UPDATED',
    cell: (info) => {
      const d = info.getValue()
      if (!d) return <span className="font-mono text-xs text-text-secondary">never</span>
      const isStale = Date.now() - new Date(d).getTime() > 3 * 24 * 60 * 60 * 1000
      return (
        <span className={cn('font-mono text-xs', isStale ? 'text-warn' : 'text-text-secondary')}>
          {fmt.isoDate(d)}
        </span>
      )
    },
  }),
]

export function UniverseGrid({ rows, onRowClick, loading, className }: UniverseGridProps) {
  return (
    <TooltipProvider>
      <DataGrid<AssetRow>
        columns={columns}
        data={rows}
        getRowId={(r) => r.name}
        onRowClick={(r) => onRowClick(r.name)}
        loading={loading}
        toolbar={{ search: false, export: false }}
        emptyState={{ title: 'No market data', body: 'Ingest the universe to begin.' }}
        className={className}
      />
    </TooltipProvider>
  )
}
