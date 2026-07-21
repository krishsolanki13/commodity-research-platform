import { Link } from 'react-router-dom'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { cn } from '@/lib/cn'
import { displayName } from '@/lib/commodity'
import { fmt } from '@/lib/fmt'

export interface PortfolioAssetTableProps {
  assetMetrics: Record<string, Record<string, number | null>>
  assets: string[]
  /** Corresponds to schema type { [key: string]: string | null } */
  assetRunIds?: Record<string, string | null>
  loading?: boolean
  className?: string
}

const missingValue = '—'

function metric(
  metrics: Record<string, number | null>,
  key: string,
  format: (value: number) => string
) {
  const value = metrics[key]
  return value == null ? missingValue : format(value)
}

export function PortfolioAssetTable({
  assetMetrics,
  assets,
  assetRunIds,
  loading = false,
  className,
}: PortfolioAssetTableProps) {
  if (loading) {
    return <LoadingSkeleton variant="table" rows={assets.length || 5} className={className} />
  }

  return (
    <table
      role="grid"
      aria-label="Per-asset performance"
      className={cn('w-full border-collapse text-sm', className)}
    >
      <thead className="bg-bg-raised">
        <tr>
          {['ASSET', 'SHARPE', 'MAX DD', 'RETURN', 'WIN RATE', 'TRADES'].map((heading) => (
            <th
              key={heading}
              scope="col"
              className="px-3 py-2 text-left text-xs font-medium text-text-secondary"
            >
              {heading}
            </th>
          ))}
          {assetRunIds !== undefined ? (
            <th className="px-3 py-2 text-right text-xs uppercase tracking-wider text-text-secondary">
              VIEW
            </th>
          ) : null}
        </tr>
      </thead>
      <tbody>
        {assets.map((asset) => {
          const metrics = assetMetrics[asset] ?? {}
          const sharpe = metrics.sharpe
          const maxDrawdown = metrics.max_drawdown
          const totalReturn = metrics.total_return
          const winRate = metrics.win_rate
          const trades = metrics.avg_trade_duration_bars ?? metrics.turnover
          const runId = assetRunIds?.[asset]

          return (
            <tr key={asset} className="border-border-subtle border-b">
              <td className="px-3 py-2 text-left font-medium text-text-primary">
                {displayName(asset)}
              </td>
              <td
                className="px-3 py-2"
                style={{
                  color:
                    sharpe == null
                      ? 'var(--text-secondary)'
                      : sharpe >= 0
                        ? 'var(--text-gain)'
                        : 'var(--text-loss)',
                }}
              >
                {metric(metrics, 'sharpe', fmt.ratio)}
              </td>
              <td
                className="px-3 py-2"
                style={{
                  color: maxDrawdown == null ? 'var(--text-secondary)' : 'var(--text-loss)',
                }}
              >
                {metric(metrics, 'max_drawdown', fmt.drawdown)}
              </td>
              <td
                className="px-3 py-2"
                style={{
                  color:
                    totalReturn == null
                      ? 'var(--text-secondary)'
                      : totalReturn >= 0
                        ? 'var(--text-gain)'
                        : 'var(--text-loss)',
                }}
              >
                {metric(metrics, 'total_return', fmt.percent)}
              </td>
              <td className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>
                {winRate == null ? missingValue : fmt.percent(winRate, { showPlus: false })}
              </td>
              <td className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>
                {trades == null ? missingValue : trades.toFixed(0)}
              </td>
              {assetRunIds !== undefined ? (
                <td className="px-3 py-2 text-right">
                  {runId ? (
                    <Link
                      to={`/runs/${runId}`}
                      className="font-mono text-xs text-text-accent hover:underline"
                      title={`View ${displayName(asset)} run detail`}
                      aria-label={`View ${displayName(asset)} run detail`}
                    >
                      View →
                    </Link>
                  ) : (
                    <span className="font-mono text-xs text-text-disabled">—</span>
                  )}
                </td>
              ) : null}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
