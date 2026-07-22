import { MetricGrid } from '@/components/data/MetricGrid'
import { AssetRiskBarChart } from '@/components/charts/AssetRiskBarChart'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type RiskReportResponse = components['schemas']['RiskReportResponse']
type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

function isApiError(error: unknown): error is ApiClientError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'apiError' in error &&
    typeof (error as ApiClientError).apiError?.status === 'number'
  )
}

interface PortfolioRiskPanelProps {
  risk: RiskReportResponse | null
  summary?: PortfolioSummaryResponse | null
  loading?: boolean
  error?: ApiClientError | Error | null
}

export function PortfolioRiskPanel({ risk, summary, loading, error }: PortfolioRiskPanelProps) {
  const isServerRestartLoss =
    !!error && isApiError(error) && error.apiError.status === 404 && !!summary

  if (isServerRestartLoss) {
    return (
      <div className="flex items-center gap-2 p-4 text-xs text-text-secondary">
        <span>Detailed analytics unavailable after server restart.</span>
        <span className="ml-1 text-text-disabled">Re-run the portfolio analysis to restore.</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="mb-2 font-mono text-xs uppercase text-text-secondary">Risk Metrics</p>
        <MetricGrid
          loading={loading}
          columns={4}
          metrics={[
            {
              label: 'VAR 95%',
              value: risk?.portfolio_var_95,
              format: 'compactUsd',
              tone: 'neutral',
            },
            {
              label: 'VAR 99%',
              value: risk?.portfolio_var_99,
              format: 'compactUsd',
              tone: 'neutral',
            },
            {
              label: 'ES 99%',
              value: risk?.portfolio_es_99,
              format: 'compactUsd',
              tone: 'neutral',
            },
            {
              label: 'DIVERSIFICATION',
              value: risk?.portfolio_diversification_benefit,
              format: 'ratio',
              tone: 'neutral',
              hint: 'Ratio of standalone asset VaR to portfolio VaR',
            },
          ]}
        />
        <p className="mt-2 font-mono text-xs text-text-secondary">
          Historical simulation VaR — realized strategy P&L over 252 days. Positive values = loss
          magnitudes.
        </p>
      </div>
      {risk?.asset_var_99 && Object.keys(risk.asset_var_99).length > 0 && (
        <AssetRiskBarChart
          assetVar99={risk.asset_var_99}
          assets={Object.keys(risk.asset_var_99).sort()}
          title="Per-Asset VaR 99% (Strategy P&L)"
          height={220}
          loading={loading}
        />
      )}
      <div>
        <p className="mb-2 font-mono text-xs uppercase text-text-secondary">Notional Exposure</p>
        <MetricGrid
          loading={loading}
          columns={4}
          metrics={[
            {
              label: 'GROSS NOTIONAL',
              value: risk?.total_avg_gross_notional,
              format: 'compactUsd',
              tone: 'neutral',
            },
            {
              label: 'NET NOTIONAL',
              value: risk?.total_avg_net_notional,
              format: 'compactUsd',
            },
          ]}
        />
      </div>
    </div>
  )
}
