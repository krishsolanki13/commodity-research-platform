import type { AssetSnapshotWithLabel } from '@/api/hooks/useCurveSnapshots'
import { RegimeBadge, type RegimeBadgeProps } from '@/components/data/RegimeBadge'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'

interface RegimeComparisonTableProps {
  snapshots: AssetSnapshotWithLabel[]
  loading?: boolean
  className?: string
}

function slopeTone(v: number | null): string {
  if (v === null) return 'var(--text-secondary)'
  return v >= 0 ? 'var(--text-warn)' : 'var(--text-gain)'
}

function rollYieldTone(v: number | null): string {
  if (v === null) return 'var(--text-secondary)'
  return v >= 0 ? 'var(--text-gain)' : 'var(--text-warn)'
}

function formatSlope(v: number | null): string {
  if (v === null) return '?'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%/yr`
}

function formatRollYield(v: number | null): string {
  if (v === null) return '?'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%/yr`
}

export function RegimeComparisonTable({
  snapshots,
  loading,
  className,
}: RegimeComparisonTableProps) {
  if (loading) {
    return <LoadingSkeleton variant="table" rows={snapshots.length || 3} className={className} />
  }

  return (
    <div className="overflow-hidden rounded border border-border-default">
    <table
      role="grid"
      aria-label="Regime comparison table"
      className={cn('w-full table-fixed border-collapse text-sm', className)}
    >
      <thead className="bg-bg-raised">
        <tr>
          <th className="px-3 py-2 text-left text-xs uppercase tracking-wider text-text-secondary">
            ASSET
          </th>
          <th className="px-3 py-2 text-left text-xs uppercase tracking-wider text-text-secondary">
            REGIME
          </th>
          <th className="px-3 py-2 text-right text-xs uppercase tracking-wider text-text-secondary">
            FRONT PRICE
          </th>
          <th className="px-3 py-2 text-right text-xs uppercase tracking-wider text-text-secondary">
            SLOPE
          </th>
          <th className="px-3 py-2 text-right text-xs uppercase tracking-wider text-text-secondary">
            ROLL YIELD
          </th>
        </tr>
      </thead>
      <tbody>
        {snapshots.map((snapshot) => (
          <tr key={snapshot.asset} className="border-t border-border-default hover:bg-bg-hover">
            <td className="px-3 py-2">
              <div className="font-medium text-text-emphasis">{snapshot.label}</div>
              <div className="font-mono text-xs text-text-secondary">{snapshot.asset}</div>
            </td>
            <td className="px-3 py-2">
              <RegimeBadge
                regime={snapshot.snapshot.regime as RegimeBadgeProps['regime']}
                size="sm"
              />
            </td>
            <td className="px-3 py-2 text-right font-mono">
              {snapshot.snapshot.front_price != null
                ? fmt.price(snapshot.snapshot.front_price, snapshot.asset)
                : '?'}
            </td>
            <td
              className="px-3 py-2 text-right font-mono"
              style={{ color: slopeTone(snapshot.snapshot.annualized_slope_pct) }}
            >
              {formatSlope(snapshot.snapshot.annualized_slope_pct)}
            </td>
            <td
              className="px-3 py-2 text-right font-mono"
              style={{ color: rollYieldTone(snapshot.snapshot.roll_yield_annualized) }}
            >
              {formatRollYield(snapshot.snapshot.roll_yield_annualized)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  )
}
