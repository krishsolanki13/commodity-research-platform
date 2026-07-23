import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']
type PortfolioEquityResponse = components['schemas']['PortfolioEquityResponse']
type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

const EMPTY_SERIES: ColumnarSeries = { index: [], columns: { value: [] } }

function computePortfolioDrawdown(equity: (number | null)[]): (number | null)[] {
  let peak = -Infinity
  return equity.map((v) => {
    if (v === null) return null
    if (v > peak) peak = v
    return peak > 0 ? (v - peak) / peak : 0
  })
}

function isApiError(error: unknown): error is ApiClientError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'apiError' in error &&
    typeof (error as ApiClientError).apiError?.status === 'number'
  )
}

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
  const isServerRestartLoss =
    !!error && isApiError(error) && error.apiError.status === 404 && !!summary

  if (isServerRestartLoss) {
    return (
      <div className="flex items-center gap-2 p-4 text-xs text-text-secondary">
        <span>Detailed analytics unavailable after server restart.</span>
        <span className="ml-1 text-text-secondary">Re-run the portfolio analysis to restore.</span>
      </div>
    )
  }

  const equityValues = equityData?.portfolio_equity?.columns?.value ?? []
  const equityIndex = equityData?.portfolio_equity?.index ?? []
  const drawdownValues = computePortfolioDrawdown(equityValues)
  const drawdownSeries: ColumnarSeries | undefined = equityData
    ? { index: equityIndex, columns: { value: drawdownValues } }
    : undefined

  return (
    <div className="flex flex-col gap-2">
      <EquityCurveChart
        equity={equityData?.portfolio_equity ?? EMPTY_SERIES}
        drawdown={drawdownSeries}
        baseline={summary?.initial_capital_total ?? 6_000_000}
        height={380}
        loading={loading}
        error={error}
        title="Portfolio Equity Curve"
      />
      {summary && (
        <p className="mt-1 font-mono text-xs text-text-secondary">
          Inner-join alignment: {summary.portfolio_date_range_from} →{' '}
          {summary.portfolio_date_range_to} · {summary.portfolio_date_range_bars} trading days
        </p>
      )}
      {(summary?.skipped_assets?.length ?? 0) > 0 && (
        <p className="mt-1 text-xs text-warn">
          ⚠ {summary!.skipped_assets.join(', ')} skipped (pipeline failure)
        </p>
      )}
    </div>
  )
}
