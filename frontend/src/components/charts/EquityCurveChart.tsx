/**
 * EquityCurveChart — portfolio/strategy equity curve with attached drawdown pane.
 *
 * Layout: two-pane (equity 65% + drawdown 20%) or single-pane (no drawdown prop).
 * Drawdown yAxis: max: 0 — forces 0 at the TOP of the pane so depth reads downward.
 * Compare mode: normalises all series to 0% at their first data point.
 *
 * CRITICAL: connectNulls: false on ALL series — gaps, never interpolation.
 *
 * Does NOT: compute drawdown from equity, fetch data.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { fmtDate } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

export interface NamedSeries {
  name: string
  equity: ColumnarSeries
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface EquityCurveChartInnerProps {
  equity: ColumnarSeries
  drawdown?: ColumnarSeries
  baseline?: number
  compare?: NamedSeries[]
  theme: EChartsTheme
}

interface EquityCurveChartProps {
  equity: ColumnarSeries
  drawdown?: ColumnarSeries
  baseline?: number
  compare?: NamedSeries[]
  // ChartFrame passthrough
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  syncGroup?: string
  onRetry?: () => void
}

// ---------------------------------------------------------------------------
// Inner component
// ---------------------------------------------------------------------------

function EquityCurveChartInner({
  equity,
  drawdown,
  baseline,
  compare,
  theme,
}: EquityCurveChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const isCompare = compare && compare.length > 0
    const showDrawdown = !isCompare && !!drawdown
    const eqCols = equity.columns as Record<string, (number | null)[]>
    const eqValues = eqCols['value'] ?? []
    const eqIndex = equity.index

    // ---------------------------------------------------------------------------
    // Grid layout
    // ---------------------------------------------------------------------------
    const grids = showDrawdown
      ? [
          // Increase gap between panes so $0 / 0.0% labels do not overlap at the seam.
          { left: 70, right: 16, top: '5%', height: '60%' },
          { left: 70, right: 16, bottom: 60, height: '18%' },
        ]
      : [{ left: 70, right: 16, top: '5%', bottom: 60 }]

    // ---------------------------------------------------------------------------
    // X axes
    // ---------------------------------------------------------------------------
    const xAxes = showDrawdown
      ? [
          {
            gridIndex: 0,
            type: 'category' as const,
            data: eqIndex,
            axisLabel: { show: false },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false },
          },
          {
            gridIndex: 1,
            type: 'category' as const,
            data: eqIndex,
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
              formatter: (value: number) => fmtDate(value),
            },
            splitLine: { show: false },
          },
        ]
      : [
          {
            type: 'category' as const,
            data: eqIndex,
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
              formatter: (value: number) => fmtDate(value),
            },
          },
        ]

    // ---------------------------------------------------------------------------
    // Y axes
    // ---------------------------------------------------------------------------
    const equityYAxis = {
      gridIndex: 0,
      // Autoscale to data range so small equity moves are visible (not flat at $1M).
      min: isCompare ? undefined : ('dataMin' as const),
      axisLabel: {
        color: theme.secondaryText,
        fontFamily: theme.monoFont,
        fontSize: 11,
        formatter: isCompare
          ? (v: number) => `${v.toFixed(1)}%`
          : (v: number) =>
              v >= 1_000_000
                ? `$${(v / 1_000_000).toFixed(2)}M`
                : v >= 1_000
                  ? `$${(v / 1_000).toFixed(0)}k`
                  : `$${v}`,
      },
      splitLine: { lineStyle: { color: theme.gridlineColor } },
    }

    // CRITICAL: max: 0 — forces 0 at the top of the drawdown pane.
    // Negative drawdown values go DOWNWARD, matching visual expectation.
    const drawdownYAxis = {
      gridIndex: 1,
      max: 0,
      name: 'Drawdown',
      nameLocation: 'middle',
      nameRotate: 90,
      nameGap: 40,
      nameTextStyle: {
        color: theme.secondaryText,
        fontFamily: theme.monoFont,
        fontSize: 11,
      },
      axisLabel: {
        color: theme.secondaryText,
        fontFamily: theme.monoFont,
        fontSize: 11,
        formatter: (value: number) => (value * 100).toFixed(1) + '%',
      },
      splitLine: { lineStyle: { color: theme.gridlineColor } },
    }

    const yAxes = showDrawdown ? [equityYAxis, drawdownYAxis] : [equityYAxis]

    // ---------------------------------------------------------------------------
    // Series
    // ---------------------------------------------------------------------------
    let equitySeries

    if (isCompare) {
      // Normalise equity to % return from first data point
      const firstEq = eqValues.find((v) => v != null) ?? 1
      const normEqData = eqValues.map((v) => (v != null ? (v / firstEq - 1) * 100 : null))
      equitySeries = {
        type: 'line' as const,
        name: 'Current',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: normEqData,
        connectNulls: false, // ← null gap policy
        lineStyle: { color: theme.amber, width: 1.5 },
        itemStyle: { color: theme.amber },
        symbol: 'none',
      }
    } else {
      equitySeries = {
        type: 'line' as const,
        name: 'Equity',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: eqValues,
        connectNulls: false, // ← null gap policy
        lineStyle: { color: theme.amber, width: 1.5 },
        itemStyle: { color: theme.amber },
        symbol: 'none',
        markLine:
          baseline != null
            ? {
                silent: true,
                symbol: 'none',
                label: {
                  formatter: 'Initial Capital',
                  color: theme.secondaryText,
                  fontFamily: theme.monoFont,
                  fontSize: 10,
                },
                lineStyle: { type: 'dotted', color: theme.secondaryText, width: 1 },
                data: [{ yAxis: baseline }],
              }
            : undefined,
      }
    }

    const compareSeries = isCompare
      ? compare.map((ns, idx) => {
          const cols = ns.equity.columns as Record<string, (number | null)[]>
          const vals = cols['value'] ?? []
          const firstVal = vals.find((v) => v != null) ?? 1
          const normData = vals.map((v) => (v != null ? (v / firstVal - 1) * 100 : null))
          return {
            type: 'line' as const,
            name: ns.name,
            xAxisIndex: 0,
            yAxisIndex: 0,
            data: normData,
            connectNulls: false, // ← null gap policy
            lineStyle: { color: theme.seriesPalette[idx % 6], width: 1.5 },
            itemStyle: { color: theme.seriesPalette[idx % 6] },
            symbol: 'none',
          }
        })
      : []

    const drawdownSeries = showDrawdown
      ? [
          {
            type: 'line' as const,
            name: 'Drawdown',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: (drawdown.columns as Record<string, (number | null)[]>)['value'] ?? [],
            connectNulls: false, // ← null gap policy
            lineStyle: { color: theme.loss, width: 1 },
            itemStyle: { color: theme.loss },
            symbol: 'none',
            areaStyle: { color: theme.lossFill },
          },
        ]
      : []

    const dataZoom = [
      {
        type: 'slider' as const,
        bottom: 8,
        xAxisIndex: showDrawdown ? [0, 1] : [0],
        height: 20,
      },
      {
        type: 'inside' as const,
        xAxisIndex: showDrawdown ? [0, 1] : [0],
      },
    ]

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
        type: 'cross',
        label: {
          backgroundColor: theme.axisPointer.label.backgroundColor,
          color: theme.axisPointer.label.color,
          fontFamily: theme.monoFont,
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
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
            name?: string | number
            value?: number | [number, number] | null
            marker?: string
          }>
          const axisRaw = items[0]?.axisValue ?? items[0]?.name
          const axisMs = typeof axisRaw === 'number' ? axisRaw : Number(axisRaw)
          const date = Number.isFinite(axisMs) ? fmtDate(axisMs) : String(axisRaw ?? '')

          return items
            .map((p) => {
              const raw = Array.isArray(p.value) ? p.value[1] : p.value
              const num = Number(raw ?? 0)
              if (p.seriesName === 'Drawdown') {
                const pct = (num * 100).toFixed(2)
                return `${date} · ${pct}%`
              }
              const marker = p.marker ?? ''
              if (isCompare) {
                return `${marker}${p.seriesName}: ${num.toFixed(2)}%`
              }
              const formatted =
                Math.abs(num) >= 1_000_000
                  ? `$${(num / 1_000_000).toFixed(2)}M`
                  : Math.abs(num) >= 1_000
                    ? `$${(num / 1_000).toFixed(1)}k`
                    : `$${num.toFixed(0)}`
              return `${marker}${p.seriesName}: ${formatted}`
            })
            .join('<br/>')
        },
      },
      legend: isCompare
        ? {
            top: 0,
            textStyle: { color: theme.secondaryText, fontFamily: theme.monoFont, fontSize: 11 },
          }
        : undefined,
      dataZoom,
      series: [equitySeries, ...compareSeries, ...drawdownSeries],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [equity, drawdown, baseline, compare, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component
// ---------------------------------------------------------------------------

export function EquityCurveChart({
  equity,
  drawdown,
  baseline,
  compare,
  title,
  height = 400,
  loading,
  error,
  syncGroup,
  onRetry,
}: EquityCurveChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      syncGroup={syncGroup}
      onRetry={onRetry}
    >
      <EquityCurveChartInner
        equity={equity}
        drawdown={drawdown}
        baseline={baseline}
        compare={compare}
        theme={theme}
      />
    </ChartFrame>
  )
}
