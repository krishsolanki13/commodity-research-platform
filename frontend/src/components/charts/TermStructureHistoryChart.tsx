/**
 * TermStructureHistoryChart — dual-pane slope + roll-yield history.
 *
 * Architecture (same as PriceChart):
 *   TermStructureHistoryChart (outer) — ChartFrame chrome + useChartTheme()
 *   TermStructureHistoryChartInner   — owns ECharts lifecycle via ChartFrame context
 *
 * CRITICAL:
 *   - xAxis type: 'time' (observation dates as epoch-ms)
 *   - connectNulls: false on BOTH series
 *   - ISO observation_date → epoch-ms before feeding ECharts
 *
 * Does NOT: fetch data, sample monthly dates, call TermStructureAnalyzer.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type TermStructureSnapshotSummary = components['schemas']['TermStructureSnapshotSummary']

export interface TermStructureHistoryChartProps {
  snapshots: TermStructureSnapshotSummary[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  syncGroup?: string
  onRetry?: () => void
}

interface InnerProps {
  snapshots: TermStructureSnapshotSummary[]
  theme: EChartsTheme
}

function TermStructureHistoryChartInner({ snapshots, theme }: InnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const index = snapshots.map((s) => new Date(s.observation_date).getTime())

    const slopeData = snapshots.map((s, i) => [index[i], s.annualized_slope_pct ?? null])

    const rollData = snapshots.map((s, i) => [index[i], s.roll_yield_annualized ?? null])

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: [
        { top: '5%', height: '42%', left: 64, right: 16 },
        { top: '55%', height: '32%', left: 64, right: 16 },
      ],
      xAxis: [
        {
          type: 'time',
          gridIndex: 0,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: theme.gridlineColor } },
          splitLine: { show: false },
        },
        {
          type: 'time',
          gridIndex: 1,
          axisLabel: {
            color: theme.secondaryText,
            fontSize: 10,
            fontFamily: theme.monoFont,
            formatter: (v: number) => new Date(v).toISOString().slice(0, 10),
          },
          axisLine: { lineStyle: { color: theme.gridlineColor } },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          type: 'value',
          gridIndex: 0,
          axisLabel: {
            color: theme.secondaryText,
            fontSize: 10,
            fontFamily: theme.monoFont,
            formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor, opacity: 0.3 } },
        },
        {
          type: 'value',
          gridIndex: 1,
          axisLabel: {
            color: theme.secondaryText,
            fontSize: 10,
            fontFamily: theme.monoFont,
            formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor, opacity: 0.3 } },
        },
      ],
      dataZoom: [
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          bottom: 4,
          height: 16,
          borderColor: theme.gridlineColor,
          fillerColor: `${theme.amber}22`,
          handleStyle: { color: theme.amber },
        },
        {
          type: 'inside',
          xAxisIndex: [0, 1],
        },
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', lineStyle: { color: theme.gridlineColor } },
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
      },
      series: [
        {
          name: 'Slope %/yr',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: slopeData,
          connectNulls: false,
          symbol: 'none',
          lineStyle: { color: theme.amber, width: 1.5 },
          itemStyle: { color: theme.amber },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [{ yAxis: 0 }],
            lineStyle: { color: theme.secondaryText, type: 'solid', width: 1, opacity: 0.4 },
          },
        },
        {
          name: 'Roll Yield %/yr',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: rollData,
          connectNulls: false,
          symbol: 'none',
          lineStyle: { color: theme.amber, width: 1.5 },
          itemStyle: { color: theme.amber },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [{ yAxis: 0 }],
            lineStyle: { color: theme.secondaryText, type: 'solid', width: 1, opacity: 0.4 },
          },
        },
      ],
    })

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [snapshots, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function TermStructureHistoryChart({
  snapshots,
  title,
  height = 320,
  loading,
  error,
  syncGroup,
  onRetry,
}: TermStructureHistoryChartProps) {
  const theme = useChartTheme()
  const isEmpty = !loading && !error && snapshots.length === 0

  return (
    <ChartFrame
      height={height}
      title={title}
      loading={loading}
      error={error}
      empty={isEmpty ? { message: 'No history data available for this asset.' } : undefined}
      syncGroup={syncGroup}
      onRetry={onRetry}
    >
      {!isEmpty && <TermStructureHistoryChartInner snapshots={snapshots} theme={theme} />}
    </ChartFrame>
  )
}
