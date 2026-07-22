import { useState } from 'react'
import { usePortfolioAssets } from '@/api/hooks/usePortfolioAssets'
import { PortfolioAssetTable } from '@/components/data/PortfolioAssetTable'

interface PortfolioPerAssetPanelProps {
  runId: string
  assets: string[]
}

export function PortfolioPerAssetPanel({ runId, assets }: PortfolioPerAssetPanelProps) {
  const [open, setOpen] = useState(false)
  const { data, isLoading, error } = usePortfolioAssets(runId)
  const assetRunIds = data?.asset_run_ids

  if (error) {
    return (
      <div className="rounded border border-border-default">
        <p className="p-4 text-xs text-text-secondary">
          Per-asset data not available for this run. Re-run the portfolio backtest to generate
          per-asset metrics.
        </p>
      </div>
    )
  }

  return (
    <section className="rounded border border-border-default">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="per-asset-table"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <span className="font-mono text-sm text-text-primary">
          Per-Asset Performance {open ? '▲' : '▼'}
        </span>
        <span className="text-xs text-text-secondary">{assets.length} assets</span>
      </button>
      {open ? (
        <div id="per-asset-table" className="border-t border-border-default p-4">
          <PortfolioAssetTable
            assets={data?.assets ?? assets}
            assetMetrics={data?.asset_metrics ?? {}}
            assetRunIds={assetRunIds}
            loading={isLoading}
          />
        </div>
      ) : null}
    </section>
  )
}
