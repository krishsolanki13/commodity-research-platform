/**
 * RollingMetricChart — rolling Sharpe + rolling drawdown over time.
 *
 * Architecture:
 *   RollingMetricChart (outer) — renders ChartFrame, calls useChartTheme()
 *   RollingMetricChartInner   — accesses ChartFrameCtx, owns the ECharts lifecycle
 *
 * All rolling computations are client-side display transforms — zero API calls.
 *
 * CRITICAL:
 *   - connectNulls: false on BOTH series
 *   - drawdown yAxis: max: 0 (0 at top, depth reads downward)
 *
 * Does NOT: fetch data.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { fmtDate } from '@/lib/fmt'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

function rollingMetric(pnl: (number | null)[], w: number): (number | null)[] {
  return pnl.map((_, i) => {
    if (i < w) return null
    const slice = pnl.slice(i - w, i).filter((v): v is number => v !== null)
    if (slice.length < Math.floor(w * 0.8)) return null
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length
    const std = Math.sqrt(variance)
    return std === 0 ? 0 : (mean / std) * Math.sqrt(252)
  })
}

function rollingDrawdown(equity: (number | null)[]): (number | null)[] {
  let peak = -Infinity
  return equity.map((v) => {
    if (v === null) return null
    if (v > peak) peak = v
    return peak > 0 ? (v - peak) / peak : 0
  })
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RollingMetricChartInnerProps {
  pnl: ColumnarSeries
  equity: ColumnarSeries
  window: number
  metrics: ('sharpe' | 'drawdown')[]
  theme: EChartsTheme
}

interface RollingMetricChartProps {
  pnl: ColumnarSeries
  equity: ColumnarSeries
  window?: number
  metrics?: ('sharpe' | 'drawdown')[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: Error | null
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle, accesses ChartFrameContext
// ---------------------------------------------------------------------------

function RollingMetricChartInner({
  pnl,
  equity,
  window: w,
  metrics,
  theme,
}: RollingMetricChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const pnlCols = pnl.columns as Record<string, (number | null)[]>
    const equityCols = equity.columns as Record<string, (number | null)[]>
    const pnlValues = pnlCols['value'] ?? []
    const equityValues = equityCols['value'] ?? []

    const showSharpe = metrics.includes('sharpe')
    const showDrawdown = metrics.includes('drawdown')

    const sharpeSeries = showSharpe ? rollingMetric(pnlValues, w) : []
    const drawdownSeries = showDrawdown ? rollingDrawdown(equityValues) : []

    const yAxes = [
      ...(showSharpe
        ? [
            {
              type: 'value' as const,
              name: 'Sharpe',
              axisLabel: {
                color: theme.secondaryText,
                fontFamily: theme.monoFont,
                fontSize: 11,
                formatter: (v: number) => v.toFixed(2),
              },
              axisPointer: {
                label: {
                  formatter: (p: { value: number }) => Number(p.value).toFixed(2),
                },
              },
              splitLine: { lineStyle: { color: theme.gridlineColor } },
            },
          ]
        : []),
      ...(showDrawdown
        ? [
            {
              type: 'value' as const,
              name: 'Drawdown',
              max: 0,
              splitNumber: 4,
              minInterval: 0.02,
              axisLabel: {
                color: theme.secondaryText,
                fontFamily: theme.monoFont,
                fontSize: 11,
                formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
              },
              axisPointer: {
                label: {
                  formatter: (p: { value: number }) => Number(p.value).toFixed(2),
                },
              },
              splitLine: { show: false },
            },
          ]
        : []),
    ]

    const series = [
      ...(showSharpe
        ? [
            {
              type: 'line' as const,
              name: 'Rolling Sharpe',
              data: sharpeSeries,
              color: theme.amber,
              connectNulls: false,
              showSymbol: false,
              yAxisIndex: 0,
              markLine: {
                silent: true,
                data: [{ yAxis: 0 }],
                lineStyle: { type: 'dashed' as const, color: theme.secondaryText },
              },
            },
          ]
        : []),
      ...(showDrawdown
        ? [
            {
              type: 'line' as const,
              name: 'Rolling Drawdown',
              data: drawdownSeries,
              color: theme.loss,
              areaStyle: { color: theme.lossFill },
              connectNulls: false,
              showSymbol: false,
              yAxisIndex: showSharpe ? 1 : 0,
            },
          ]
        : []),
    ]

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 60, right: 60, top: '12%', bottom: '10%' },
      legend: { show: true },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          lineStyle: { color: theme.gridlineColor },
          label: {
            backgroundColor: theme.tooltip.backgroundColor,
            color: theme.secondaryText,
            fontSize: 10,
            fontFamily: theme.monoFont,
            formatter: (p: { value: number | string }) =>
              typeof p.value === 'number' && p.value > 1e9
                ? fmtDate(p.value)
                : String(p.value),
          },
        },
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
          fontSize: 12,
        },
        formatter: (params: unknown) => {
          const items = (Array.isArray(params) ? params : [params]) as Array<{
            seriesName?: string
            axisValue?: string | number
            value?: number | [number, number] | null
            marker?: string
          }>
          const axisRaw =
            items[0]?.axisValue ?? (Array.isArray(items[0]?.value) ? items[0]?.value[0] : undefined)
          const axisMs = typeof axisRaw === 'number' ? axisRaw : Number(axisRaw)
          const date = Number.isFinite(axisMs) ? fmtDate(axisMs) : String(axisRaw ?? '')
          const lines = items.map((p) => {
            const raw = Array.isArray(p.value) ? p.value[1] : p.value
            return `${p.marker ?? ''}${p.seriesName}: ${Number(raw ?? 0).toFixed(3)}`
          })
          return [date, ...lines].join('<br/>')
        },
      },
      xAxis: {
        type: 'category' as const,
        data: pnl.index,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (value: number) => fmtDate(value),
        },
        axisPointer: {
          label: { formatter: (p: { value: number }) => fmtDate(p.value) },
        },
      },
      yAxis: yAxes,
      series,
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [pnl, equity, w, metrics, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function RollingMetricChart({
  pnl,
  equity,
  window = 63,
  metrics = ['sharpe', 'drawdown'],
  title,
  height = 280,
  loading,
  error,
}: RollingMetricChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading} error={error}>
      <RollingMetricChartInner
        pnl={pnl}
        equity={equity}
        window={window}
        metrics={metrics}
        theme={theme}
      />
    </ChartFrame>
  )
}
