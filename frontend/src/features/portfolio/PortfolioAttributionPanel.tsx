import { AssetAttributionTable } from '@/components/data/AssetAttributionTable'
import { AssetSharpeBarChart } from '@/components/charts/AssetSharpeBarChart'
import { MetricGrid } from '@/components/data/MetricGrid'
import type { MetricStatProps } from '@/components/data/MetricStat'
import type { components } from '@/api/schema'

type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']
type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']
type PortfolioAssetsResponse = components['schemas']['PortfolioAssetsResponse']

interface PortfolioAttributionPanelProps {
  summary: PortfolioSummaryResponse | null
  correlation: CorrelationReportResponse | null
  assetsData?: PortfolioAssetsResponse | null
  assetsLoading?: boolean
  loading?: boolean
}

export function PortfolioAttributionPanel({
  summary,
  correlation,
  assetsData,
  assetsLoading = false,
  loading,
}: PortfolioAttributionPanelProps) {
  const assets = summary?.assets ?? []
  const volMetrics: MetricStatProps[] = assets.map((asset) => ({
    label: asset.toUpperCase().replace('_', ' '),
    value: correlation?.realized_vol_by_asset[asset],
    format: 'percent',
    tone: 'neutral',
  }))

  if (correlation?.portfolio_realized_vol != null) {
    volMetrics.push({
      label: 'PORTFOLIO',
      value: correlation.portfolio_realized_vol,
      format: 'percent',
      tone: 'neutral',
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="mb-2 font-mono text-xs uppercase text-text-secondary">
          Asset P&L Attribution (USD)
        </p>
        <div className="overflow-hidden rounded border border-border-default">
          <AssetAttributionTable
            absolutePnlByAsset={summary?.absolute_pnl_by_asset ?? {}}
            assets={assets}
            initialCapitalPerAsset={summary?.initial_capital_per_asset ?? 1_000_000}
            loading={loading}
          />
        </div>
      </div>
      {assetsData?.asset_metrics && assets.length > 0 && (
        <AssetSharpeBarChart
          assetMetrics={assetsData.asset_metrics}
          assets={assets}
          title="Per-Asset Sharpe Ratio"
          height={220}
          loading={assetsLoading}
          empty={{ message: 'Per-asset metrics not available. Re-run portfolio to generate.' }}
        />
      )}
      <div>
        <p className="mb-2 font-mono text-xs uppercase text-text-secondary">
          Strategy Realized Vol (%)
        </p>
        <MetricGrid loading={loading} metrics={volMetrics} columns={6} />
        <p className="mt-2 font-mono text-xs italic text-text-secondary">
          Strategy P&L volatility — not commodity price volatility
        </p>
      </div>
    </div>
  )
}
