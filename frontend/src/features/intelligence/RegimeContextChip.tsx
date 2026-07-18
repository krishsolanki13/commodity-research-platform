import { cn } from '@/lib/cn'
import { RegimeBadge } from '@/components/data/RegimeBadge'
import { useCurveSnapshot } from '@/api/hooks/useCurveSnapshot'
import type { Regime } from '@/lib/tone'

interface RegimeContextChipProps {
  asset: string
  compact?: boolean
}

export function RegimeContextChip({ asset, compact = false }: RegimeContextChipProps) {
  const { data, isLoading } = useCurveSnapshot(asset, 2, undefined)

  // Fail silently — chip is supplementary context only.
  // Must return null for: loading, error, no data. No spinners, no error messages.
  if (isLoading || !data) return null

  return (
    <div
      role="status"
      aria-label={`${asset} term structure regime: ${data.regime}`}
      className="flex items-center gap-2 text-xs"
    >
      {!compact && <span className="font-mono text-text-secondary">Term structure:</span>}
      <RegimeBadge regime={data.regime as Regime} size="sm" />
      {!compact &&
        data.annualized_slope_pct != null &&
        !Number.isNaN(data.annualized_slope_pct) && (
          <span
            className={cn('font-mono', data.regime === 'backwardation' ? 'text-gain' : 'text-warn')}
          >
            {data.annualized_slope_pct >= 0 ? '+' : ''}
            {(data.annualized_slope_pct * 100).toFixed(2)}%/yr
          </span>
        )}
    </div>
  )
}
