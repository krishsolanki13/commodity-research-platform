import { useEffect, useRef, useState } from 'react'
import type { EChartsOption } from 'echarts'
import { CorrelationHeatmapChart } from '@/components/charts/CorrelationHeatmapChart'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']
type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']

interface PortfolioCorrelationPanelProps {
  correlation: CorrelationReportResponse | null
  loading?: boolean
}

function generatePairs(assets: string[]): [string, string][] {
  const sorted = [...assets].sort()
  const pairs: [string, string][] = []
  sorted.forEach((a, i) => {
    sorted.slice(i + 1).forEach((b) => pairs.push([a, b]))
  })
  return pairs
}

interface RollingCorrelationChartInnerProps {
  series: ColumnarSeries
  theme: EChartsTheme
}

function RollingCorrelationChartInner({ series, theme }: RollingCorrelationChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const values = series.columns.value ?? []
    const option: EChartsOption = {
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 52, right: 16, top: '8%', bottom: 38 },
      xAxis: {
        type: 'time',
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        min: -1,
        max: 1,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
          fontSize: 12,
        },
      },
      series: [
        {
          type: 'line',
          data: series.index.map((timestamp, index) => [timestamp, values[index] ?? null]),
          connectNulls: false,
          symbol: 'none',
          lineStyle: { color: theme.amber, width: 1.5 },
          itemStyle: { color: theme.amber },
        },
      ],
    }
    chart.setOption(option)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [series, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

function RollingCorrelationChart({
  series,
  loading,
}: {
  series?: ColumnarSeries
  loading?: boolean
}) {
  const theme = useChartTheme()
  const emptySeries: ColumnarSeries = { index: [], columns: { value: [] } }

  return (
    <ChartFrame
      height={192}
      loading={loading}
      empty={!loading && !series ? { message: 'No rolling data for this pair' } : undefined}
    >
      <RollingCorrelationChartInner series={series ?? emptySeries} theme={theme} />
    </ChartFrame>
  )
}

export function PortfolioCorrelationPanel({
  correlation,
  loading,
}: PortfolioCorrelationPanelProps) {
  const assets = correlation
    ? Object.keys(correlation.correlation_matrix).sort()
    : []
  const pairs = generatePairs(assets)

  const [selectedPair, setSelectedPair] = useState<[string, string]>(
    ['brent', 'wti']
  )
  const [window, setWindow] = useState<63 | 126>(63)

  const [lo, hi] = [...selectedPair].sort() as [string, string]
  const rollingSeries =
    window === 63
      ? correlation?.rolling_correlations_63?.[lo]?.[hi]
      : correlation?.rolling_correlations_126?.[lo]?.[hi]

  return (
    <div className="flex flex-col gap-6">
      <CorrelationHeatmapChart
        correlationMatrix={correlation?.correlation_matrix ?? {}}
        assets={assets}
        height={320}
        loading={loading}
      />

      <div className="flex gap-6 text-xs font-mono text-text-secondary">
        <span>
          Avg Correlation:{' '}
          <span className="text-text-primary">
            {correlation?.avg_pairwise_correlation?.toFixed(3) ?? '—'}
          </span>
        </span>
        {correlation?.most_correlated_pair && (
          <span>
            Most:{' '}
            <span className="text-text-primary">
              {correlation.most_correlated_pair[0]} /{' '}
              {correlation.most_correlated_pair[1]} (
              {correlation.most_correlated_pair[2].toFixed(2)})
            </span>
          </span>
        )}
        {correlation?.least_correlated_pair && (
          <span>
            Least:{' '}
            <span className="text-text-primary">
              {correlation.least_correlated_pair[0]} /{' '}
              {correlation.least_correlated_pair[1]} (
              {correlation.least_correlated_pair[2].toFixed(2)})
            </span>
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          <select
            className="bg-bg-raised border border-border-default text-text-primary text-xs font-mono px-2 py-1 rounded"
            value={`${selectedPair[0]},${selectedPair[1]}`}
            onChange={(e) => {
              const [a, b] = e.target.value.split(',') as [string, string]
              setSelectedPair([a, b])
            }}
          >
            {pairs.map(([a, b]) => (
              <option key={`${a},${b}`} value={`${a},${b}`}>
                {a} / {b}
              </option>
            ))}
          </select>
          <div className="flex gap-1">
            {([63, 126] as const).map((w) => (
              <button
                key={w}
                onClick={() => setWindow(w)}
                className={`px-3 py-1 text-xs font-mono rounded border ${
                  window === w
                    ? 'bg-bg-accent border-border-strong text-text-primary'
                    : 'bg-bg-raised border-border-default text-text-secondary'
                }`}
              >
                {w}-day
              </button>
            ))}
          </div>
        </div>

        <div className="text-xs font-mono text-text-secondary mb-1">
          {lo} / {hi} — Rolling {window}-day Correlation
        </div>

        <RollingCorrelationChart series={rollingSeries?.data} loading={loading} />
      </div>
    </div>
  )
}
