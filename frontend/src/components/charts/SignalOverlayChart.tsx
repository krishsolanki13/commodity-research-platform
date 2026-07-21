/**
 * SignalOverlayChart — three-pane signal visualization.
 *
 * Layout:
 *   grid[0] price pane      top: 2%,  height: 48%  — candlestick
 *   grid[1] raw signal pane top: 55%, height: 20%  — line + zero markLine
 *   grid[2] position pane   bottom: 8%, height: 15% — colored bars {-1,0,+1}
 *
 * CRITICAL constraints:
 *   - Price yAxis: min: null (NEVER min: 0 — WTI negative price)
 *   - All line series: connectNulls: false
 *   - Shared crosshair: axisPointer link xAxisIndex: 'all'
 *
 * Does NOT: fetch data, compute signals.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SignalOverlayChartInnerProps {
  ohlcv: ColumnarSeries
  raw: ColumnarSeries
  position: ColumnarSeries
  theme: EChartsTheme
}

interface SignalOverlayChartProps {
  ohlcv: ColumnarSeries
  raw: ColumnarSeries
  position: ColumnarSeries
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  syncGroup?: string
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle
// ---------------------------------------------------------------------------

function SignalOverlayChartInner({ ohlcv, raw, position, theme }: SignalOverlayChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const ohlcvCols = ohlcv.columns as Record<string, (number | null)[]>
    const open = ohlcvCols['open'] ?? []
    const high = ohlcvCols['high'] ?? []
    const low = ohlcvCols['low'] ?? []
    const close = ohlcvCols['close'] ?? []
    const index = ohlcv.index

    // ECharts candlestick data order: [open, close, low, high]
    const candleData = index.map((_t, i) => {
      if (open[i] == null || close[i] == null || low[i] == null || high[i] == null) {
        return null
      }
      return [open[i], close[i], low[i], high[i]]
    })

    const rawCols = raw.columns as Record<string, (number | null)[]>
    const rawValues = rawCols['raw'] ?? []
    const rawAbs = rawValues.filter((v): v is number => v !== null).map(Math.abs)
    const absMax = rawAbs.length > 0 ? Math.max(...rawAbs) : 1

    const posCols = position.columns as Record<string, (number | null)[]>
    const posValues = posCols['position'] ?? []

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: [
        { left: 60, right: 16, top: '2%', height: '48%' },
        { left: 60, right: 16, top: '55%', height: '20%' },
        { left: 60, right: 16, bottom: '8%', height: '15%' },
      ],
      xAxis: [
        {
          gridIndex: 0,
          type: 'category' as const,
          data: index,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
        },
        {
          gridIndex: 1,
          type: 'category' as const,
          data: raw.index,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
        },
        {
          gridIndex: 2,
          type: 'category' as const,
          data: position.index,
          axisLabel: {
            show: true,
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
          },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          gridIndex: 0,
          min: null, // ← auto-scale: required for negative prices (WTI)
          axisLabel: {
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor } },
        },
        {
          gridIndex: 1,
          min: -absMax,
          max: absMax,
          axisLabel: {
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor } },
        },
        {
          gridIndex: 2,
          min: -1.5,
          max: 1.5,
          axisLabel: {
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
            formatter: (v: number) => (v > 0 ? 'Long' : v < 0 ? 'Short' : 'Flat'),
          },
          splitLine: { show: false },
        },
      ],
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
      },
      series: [
        {
          type: 'candlestick' as const,
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: candleData,
          connectNulls: false,
          itemStyle: {
            color: theme.gain,
            color0: theme.loss,
            borderColor: theme.gain,
            borderColor0: theme.loss,
          },
        },
        {
          type: 'line' as const,
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: rawValues,
          connectNulls: false, // ← mandatory: gaps, never interpolate nulls
          lineStyle: { color: theme.amber, width: 1.5 },
          itemStyle: { color: theme.amber },
          symbol: 'none',
          markLine: {
            silent: true,
            data: [{ yAxis: 0 }],
            lineStyle: { color: theme.secondaryText, type: 'dashed' },
          },
        },
        {
          type: 'bar' as const,
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: posValues,
          itemStyle: {
            // ECharts callback param typing is incomplete — cast from unknown per §17
            color: (params: unknown) => {
              const p = params as { value: [number, number] | number }
              const v = Array.isArray(p.value) ? p.value[1] : p.value
              if (v > 0) return theme.gainFill
              if (v < 0) return theme.lossFill
              return theme.gridlineColor
            },
          },
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [ohlcv, raw, position, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function SignalOverlayChart({
  ohlcv,
  raw,
  position,
  title,
  height = '65vh',
  loading,
  error,
  syncGroup,
}: SignalOverlayChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading} error={error} syncGroup={syncGroup}>
      <SignalOverlayChartInner ohlcv={ohlcv} raw={raw} position={position} theme={theme} />
    </ChartFrame>
  )
}
