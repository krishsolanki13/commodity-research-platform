import { MetricGrid } from '@/components/data/MetricGrid'
import { MetricStat } from '@/components/data/MetricStat'
import { AssetRiskBarChart } from '@/components/charts/AssetRiskBarChart'
import { ContributionToRiskChart } from '@/components/charts/ContributionToRiskChart'
import { pct, dec } from '@/lib/fmt'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'
import type { components } from '@/api/schema'

type RiskReportResponse = components['schemas']['RiskReportResponse']

interface PortfolioRiskPanelProps {
  risk: RiskReportResponse | null
  loading?: boolean
}

function CalibrationValue({ pvalue }: { pvalue: number | null | undefined }) {
  if (pvalue == null) {
    return (
      <TooltipProvider delayDuration={300}>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="cursor-help font-mono font-medium text-metric text-text-secondary">
              —
            </span>
          </TooltipTrigger>
          <TooltipContent>
            <p className="max-w-xs">Insufficient data</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  if (pvalue >= 0.05) {
    return (
      <span className="font-mono font-medium text-metric text-gain">✓ Calibrated</span>
    )
  }

  return (
    <span className="font-mono font-medium text-metric text-loss">✗ Miscalibrated</span>
  )
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
      {risk?.asset_var_99 && Object.keys(risk.asset_var_99).length > 0 && (
        <AssetRiskBarChart
          assetVar99={risk.asset_var_99}
          assets={Object.keys(risk.asset_var_99).sort()}
          title="Per-Asset VaR 99% (Strategy P&L)"
          height={220}
          loading={loading}
        />
      )}
      <ContributionToRiskChart
        data={risk?.asset_contribution_to_vol_pct ?? {}}
        loading={loading}
      />
      <div>
        <p className="mb-2 font-mono text-xs uppercase text-text-secondary">
          KUPIEC BACKTESTING VALIDATION
        </p>
        {loading ? (
          <MetricGrid loading columns={4} metrics={[]} />
        ) : (
          <div className="grid w-full grid-cols-5 gap-4">
            <MetricStat
              label="DAYS TESTED"
              value={
                risk?.n_backtesting_days != null
                  ? risk.n_backtesting_days.toLocaleString()
                  : null
              }
              format="raw"
              tone="neutral"
            />
            <MetricStat
              label="EXCEPTIONS 99%"
              value={risk?.exceptions_99 ?? null}
              format="integer"
              tone="neutral"
            />
            <MetricStat
              label="EXCEPTION RATE"
              value={
                risk?.exception_rate_99 != null ? pct(risk.exception_rate_99, 2) : null
              }
              format="raw"
              tone="neutral"
            />
            <MetricStat
              label="KUPIEC p-VALUE"
              value={
                risk?.kupiec_pvalue_99 != null ? dec(risk.kupiec_pvalue_99, 3) : null
              }
              format="raw"
              tone="neutral"
            />
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="text-xs uppercase tracking-wider text-text-secondary">
                CALIBRATION
              </span>
              <CalibrationValue pvalue={risk?.kupiec_pvalue_99} />
            </div>
          </div>
        )}
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
