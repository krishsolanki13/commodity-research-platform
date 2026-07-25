import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
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
  onHoverAsset?: (asset: string) => void
  loading?: boolean
  className?: string
}

const healthColorMap: Record<AssetRow['dataHealth'], string> = {
  ok: 'var(--ok-500)',
  warn: 'var(--warn-500)',
  crit: 'var(--crit-500)',
  missing: 'var(--text-disabled)',
}

const HEADERS = [
  { label: 'ASSET',   align: 'left'   },
  { label: 'LAST',    align: 'right'  },
  { label: '1D%',     align: 'right'  },
  { label: '1W%',     align: 'right'  },
  { label: '1M%',     align: 'right'  },
  { label: 'VOL 63D', align: 'right'  },
  { label: '20D',     align: 'center' },
  { label: 'HEALTH',  align: 'center' },
  { label: 'UPDATED', align: 'left'   },
] as const

export function UniverseGrid({
  rows,
  onRowClick,
  onHoverAsset,
  loading,
  className,
}: UniverseGridProps) {
  if (loading) {
    return <LoadingSkeleton variant="table" rows={6} className={className} />
  }

  return (
    <TooltipProvider>
      <div className={cn('w-full overflow-x-auto', className)}>
        <table
          className="w-full border-collapse text-sm"
          style={{ tableLayout: 'auto' }}
        >
          <thead>
            <tr className="border-b border-border-default bg-bg-raised">
              {HEADERS.map((h) => (
                <th
                  key={h.label}
                  className={cn(
                    'px-3 py-2 text-xs font-medium uppercase tracking-wider text-text-secondary',
                    h.align === 'right' && 'text-right',
                    h.align === 'center' && 'text-center',
                    h.align === 'left' && 'text-left'
                  )}
                >
                  {h.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  className="py-12 text-center text-sm text-text-secondary"
                >
                  No market data: Ingest the universe to begin.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.name}
                  onClick={() => onRowClick(row.name)}
                  onMouseEnter={
                    onHoverAsset ? () => onHoverAsset(row.name) : undefined
                  }
                  className="cursor-pointer border-b border-border-default transition-colors hover:bg-bg-hover"
                >
                  {/* ASSET */}
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-medium text-text-emphasis">
                        {row.displayName}
                      </span>
                      <span className="font-mono text-xs text-text-secondary">
                        {row.ticker}
                      </span>
                    </div>
                  </td>

                  {/* LAST */}
                  <td className="px-3 py-2.5 text-right font-mono">
                    {row.lastPrice !== null ? (
                      fmt.price(row.lastPrice, row.name)
                    ) : (
                      <span className="text-text-secondary">&mdash;</span>
                    )}
                  </td>

                  {/* 1D% */}
                  <td className="px-3 py-2.5 text-right font-mono">
                    {row.return1d !== null ? (
                      <span style={{ color: tone.pnl(row.return1d) }}>
                        {fmt.percent(row.return1d)}
                      </span>
                    ) : (
                      <span className="text-text-secondary">&mdash;</span>
                    )}
                  </td>

                  {/* 1W% */}
                  <td className="px-3 py-2.5 text-right font-mono">
                    {row.return1w !== null ? (
                      <span style={{ color: tone.pnl(row.return1w) }}>
                        {fmt.percent(row.return1w)}
                      </span>
                    ) : (
                      <span className="text-text-secondary">&mdash;</span>
                    )}
                  </td>

                  {/* 1M% */}
                  <td className="px-3 py-2.5 text-right font-mono">
                    {row.return1m !== null ? (
                      <span style={{ color: tone.pnl(row.return1m) }}>
                        {fmt.percent(row.return1m)}
                      </span>
                    ) : (
                      <span className="text-text-secondary">&mdash;</span>
                    )}
                  </td>

                  {/* VOL 63D */}
                  <td className="px-3 py-2.5 text-right font-mono">
                    {row.realizedVol63d !== null ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="text-text-primary">
                            {fmt.percent(row.realizedVol63d, { showPlus: false })}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          63d realized volatility (annualized)
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-text-secondary">&mdash;</span>
                    )}
                  </td>

                  {/* 20D sparkline */}
                  <td className="px-3 py-2.5 text-center">
                    <Sparkline
                      values={row.sparklineValues}
                      tone="auto"
                      width={80}
                      height={24}
                    />
                  </td>

                  {/* HEALTH */}
                  <td className="px-3 py-2.5 text-center">
                    {(() => {
                      const health = row.dataHealth
                      const flags = row.flaggedAnomalies
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
                              style={{
                                backgroundColor: healthColorMap[health],
                              }}
                            />
                          </TooltipTrigger>
                          <TooltipContent>{label}</TooltipContent>
                        </Tooltip>
                      )
                    })()}
                  </td>

                  {/* UPDATED */}
                  <td className="px-3 py-2.5">
                    {row.lastDate ? (
                      <span
                        className={cn(
                          'font-mono text-xs',
                          Date.now() - new Date(row.lastDate).getTime() >
                            3 * 24 * 60 * 60 * 1000
                            ? 'text-warn'
                            : 'text-text-secondary'
                        )}
                      >
                        {fmt.isoDate(row.lastDate)}
                      </span>
                    ) : (
                      <span className="font-mono text-xs text-text-secondary">
                        never
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </TooltipProvider>
  )
}
