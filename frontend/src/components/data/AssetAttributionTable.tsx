import { displayName } from '@/lib/commodity'
import { fmt } from '@/lib/fmt'
import { cn } from '@/lib/cn'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'

interface AssetAttributionTableProps {
  absolutePnlByAsset: Record<string, number>
  assets: string[]
  initialCapitalPerAsset: number
  loading?: boolean
  className?: string
}

export function AssetAttributionTable({
  absolutePnlByAsset,
  assets,
  initialCapitalPerAsset,
  loading,
  className,
}: AssetAttributionTableProps) {
  if (loading) {
    return <LoadingSkeleton variant="table" className={className} />
  }

  return (
    <table
      role="grid"
      aria-label="Asset P&L attribution"
      className={cn('w-full border-collapse text-sm', className)}
    >
      <thead className="bg-bg-raised">
        <tr>
          <th className="px-3 py-2 text-left text-xs uppercase text-text-secondary">ASSET</th>
          <th className="px-3 py-2 text-right text-xs uppercase text-text-secondary">P&L (USD)</th>
          <th className="px-3 py-2 text-right text-xs uppercase text-text-secondary">P&L (%)</th>
        </tr>
      </thead>
      <tbody>
        {assets.map((asset) => {
          const pnl = absolutePnlByAsset[asset] ?? 0
          const pnlPct = initialCapitalPerAsset > 0 ? pnl / initialCapitalPerAsset : 0
          const color = pnl >= 0 ? 'var(--text-gain)' : 'var(--text-loss)'

          return (
            <tr key={asset} className="border-t border-border-default hover:bg-bg-hover">
              <td className="px-3 py-2">
                <div className="font-medium text-text-emphasis">{displayName(asset)}</div>
                <div className="font-mono text-xs text-text-secondary">{asset}</div>
              </td>
              <td className="px-3 py-2 text-right font-mono" style={{ color }}>
                {pnl >= 0 ? '+' : ''}
                {fmt.compactUsd(pnl)}
              </td>
              <td className="px-3 py-2 text-right font-mono text-xs" style={{ color }}>
                {fmt.percent(pnlPct)}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
