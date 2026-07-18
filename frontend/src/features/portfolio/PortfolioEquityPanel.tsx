import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']
type PortfolioEquityResponse = components['schemas']['PortfolioEquityResponse']
type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

const EMPTY_SERIES: ColumnarSeries = { index: [], columns: { value: [] } }

interface PortfolioEquityPanelProps {
  equityData: PortfolioEquityResponse | null
  summary: PortfolioSummaryResponse | null
  loading?: boolean
  error?: ApiClientError | Error | null
}

export function PortfolioEquityPanel({
  equityData,
  summary,
  loading,
  error,
}: PortfolioEquityPanelProps) {
  return (
    <div className="flex flex-col gap-2">
      <EquityCurveChart
        equity={equityData?.portfolio_equity ?? EMPTY_SERIES}
        baseline={summary?.initial_capital_total ?? 6_000_000}
        height={350}
        loading={loading}
        error={error}
        title="Portfolio Equity Curve"
      />
      {summary && (
        <p className="text-xs font-mono text-text-secondary mt-1">
          Inner-join alignment: {summary.portfolio_date_range_from} →{' '}
          {summary.portfolio_date_range_to} · {summary.portfolio_date_range_bars} trading days
        </p>
      )}
      {(summary?.skipped_assets?.length ?? 0) > 0 && (
        <p className="text-xs text-warn mt-1">
          ⚠ {summary!.skipped_assets.join(', ')} skipped (pipeline failure)
        </p>
      )}
    </div>
  )
}
