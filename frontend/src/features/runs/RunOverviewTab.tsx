/**
 * RunOverviewTab — primary/secondary metrics, equity curve, rolling performance.
 * All series computed client-side from hook data. No direct API calls.
 */
import { useRunDetail, useRunSeries } from '@/api/hooks'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import { RollingMetricChart } from '@/components/charts/RollingMetricChart'
import { MetricGrid } from '@/components/data/MetricGrid'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const EMPTY_SERIES: ColumnarSeries = { index: [], columns: { value: [] } }

function rollingDrawdownFromEquity(equity: (number | null)[]): (number | null)[] {
  let peak = -Infinity
  return equity.map((v) => {
    if (v === null) return null
    if (v > peak) peak = v
    return peak > 0 ? (v - peak) / peak : 0
  })
}

interface RunOverviewTabProps {
  runId: string
}

export function RunOverviewTab({ runId }: RunOverviewTabProps) {
  const runQuery = useRunDetail(runId)
  const equityQuery = useRunSeries(runId, 'equity_curve')
  const pnlQuery = useRunSeries(runId, 'pnl')

  const metrics = runQuery.data?.metrics
  const equityValues = equityQuery.data?.data.columns.value ?? []
  const equityIndex = equityQuery.data?.data.index ?? []
  const drawdownValues = rollingDrawdownFromEquity(equityValues)

  const drawdownSeries: ColumnarSeries = {
    index: equityIndex,
    columns: { value: drawdownValues },
  }

  const equitySeries = equityQuery.data?.data ?? EMPTY_SERIES
  const pnlSeries = pnlQuery.data?.data ?? EMPTY_SERIES

  return (
    <div className="flex flex-col gap-6">
      {/* Section 1 — Primary metrics */}
      {runQuery.isLoading ? (
        <LoadingSkeleton variant="metric-grid" columns={3} />
      ) : (
        <MetricGrid
          columns={3}
          metrics={[
            { label: 'SHARPE', value: metrics?.['sharpe'], format: 'ratio', tone: 'neutral' },
            { label: 'SORTINO', value: metrics?.['sortino'], format: 'ratio', tone: 'neutral' },
            { label: 'CALMAR', value: metrics?.['calmar'], format: 'ratio', tone: 'neutral' },
            {
              label: 'MAX DD',
              value: metrics?.['max_drawdown'],
              format: 'drawdown',
              tone: 'auto',
            },
            {
              label: 'TOTAL RETURN',
              value: metrics?.['total_return'],
              format: 'percent',
              tone: 'auto',
            },
            { label: 'CAGR', value: metrics?.['cagr'], format: 'percent', tone: 'auto' },
          ]}
        />
      )}

      {/* Section 2 — Equity curve */}
      {equityQuery.isLoading ? (
        <LoadingSkeleton variant="chart" />
      ) : (
        <EquityCurveChart
          equity={equitySeries}
          drawdown={equityQuery.data ? drawdownSeries : undefined}
          baseline={runQuery.data?.metrics['initial_capital'] ?? 1_000_000}
          height={380}
          title="Equity Curve + Drawdown"
          syncGroup="run-detail"
          loading={equityQuery.isLoading}
          error={equityQuery.error ?? null}
        />
      )}

      {/* Section 3 — Secondary metrics */}
      {runQuery.isLoading ? (
        <LoadingSkeleton variant="metric-grid" columns={4} />
      ) : (
        <MetricGrid
          columns={4}
          metrics={[
            { label: 'WIN RATE', value: metrics?.['win_rate'], format: 'percent', tone: 'neutral' },
            {
              label: 'PROFIT FACTOR',
              value: metrics?.['profit_factor'],
              format: 'ratio',
              tone: 'neutral',
            },
            {
              label: 'AVG TRADE',
              value: metrics?.['avg_trade_duration_bars'],
              format: 'bars',
              tone: 'neutral',
            },
            {
              label: 'TURNOVER',
              value: metrics?.['turnover'],
              format: 'percent',
              tone: 'neutral',
            },
            { label: 'AVG WIN', value: metrics?.['avg_win'], format: 'compactUsd', tone: 'auto' },
            {
              label: 'AVG LOSS',
              value: metrics?.['avg_loss'],
              format: 'compactUsd',
              tone: 'auto',
            },
            {
              label: 'LARGEST WIN',
              value: metrics?.['largest_win'],
              format: 'compactUsd',
              tone: 'auto',
            },
            {
              label: 'LARGEST LOSS',
              value: metrics?.['largest_loss'],
              format: 'compactUsd',
              tone: 'auto',
            },
          ]}
        />
      )}

      {/* Section 4 — Rolling performance */}
      {pnlQuery.isLoading || equityQuery.isLoading ? (
        <LoadingSkeleton variant="chart" />
      ) : (
        <RollingMetricChart
          pnl={pnlSeries}
          equity={equitySeries}
          window={63}
          title="Rolling Performance (63-day)"
          height={250}
          loading={pnlQuery.isLoading || equityQuery.isLoading}
        />
      )}
    </div>
  )
}
