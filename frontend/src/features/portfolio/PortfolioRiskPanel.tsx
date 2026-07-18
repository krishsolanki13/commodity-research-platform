import { MetricGrid } from '@/components/data/MetricGrid'
import type { components } from '@/api/schema'

type RiskReportResponse = components['schemas']['RiskReportResponse']

interface PortfolioRiskPanelProps {
  risk: RiskReportResponse | null
  loading?: boolean
}

export function PortfolioRiskPanel({ risk, loading }: PortfolioRiskPanelProps) {
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
