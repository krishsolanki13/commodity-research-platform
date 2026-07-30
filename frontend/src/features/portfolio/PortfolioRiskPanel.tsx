import { MetricGrid } from '@/components/data/MetricGrid'
import { AssetRiskBarChart } from '@/components/charts/AssetRiskBarChart'
import { ContributionToRiskChart } from './ContributionToRiskChart'
import { cn } from '@/lib/cn'
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
        {/* EM4 — Kupiec VaR Calibration (Unconditional Coverage Test) */}
        {risk != null && (risk.n_backtesting_days ?? 0) > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="text-text-secondary">VaR99 Calibration</span>
            <span className="font-mono text-text-primary">
              {risk.exceptions_99} exceptions / {risk.n_backtesting_days} days{' '}
              ({((risk.exception_rate_99 ?? 0) * 100).toFixed(1)}% observed vs 1.0% expected)
            </span>
            {risk.kupiec_pvalue_99 != null && !Number.isNaN(risk.kupiec_pvalue_99) && (
              <span
                className={cn(
                  'rounded px-1.5 py-0.5 font-mono text-xs',
                  risk.kupiec_pvalue_99 > 0.05
                    ? 'bg-gain-fill text-gain'
                    : 'bg-loss-fill text-loss'
                )}
                title="Unconditional Coverage Test (Kupiec 1995). p > 0.05: cannot reject that VaR is correctly calibrated."
              >
                p={risk.kupiec_pvalue_99.toFixed(3)}
                {risk.kupiec_pvalue_99 > 0.05 ? ' calibrated' : ' miscalibrated'}
              </span>
            )}
          </div>
        )}
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
      {/* EM4 — Contribution to Strategy Volatility */}
      {risk != null &&
        Object.keys(risk.asset_contribution_to_vol_pct ?? {}).length > 0 && (
          <section className="mt-4">
            <h3 className="mb-1 text-sm font-medium text-text-secondary">
              Contribution to Strategy Volatility
            </h3>
            <p className="mb-3 text-xs text-text-secondary opacity-70">
              Per-asset share of portfolio annualized strategy P&amp;L volatility. Weights from
              average gross notional. Values sum to 100%.{' '}
              <span className="italic">
                Strategy vol (2–8%/yr), not commodity price vol (15–60%/yr).
              </span>
            </p>
            <ContributionToRiskChart data={risk.asset_contribution_to_vol_pct ?? {}} />
          </section>
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
