/**
 * SignalOverlayChart — two-pane signal visualization.
 *
 * Layout:
 *   grid[0] price pane    top: 2%,  height: 58%
 *   grid[1] signal pane   top: 63%, bottom: 36
 *
 * Long/Short periods from position data are rendered as markArea bands on
 * the signal pane only (green = Long, red = Short). The position pane is removed.
 *
 * CRITICAL constraints:
 *   - Price yAxis: min/max callbacks (supports negative prices; WTI)
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
import { fmtDate } from '@/lib/fmt'
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
  asset?: string
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

    const posCols = position.columns as Record<string, (number | null)[]>
    const posValues = posCols['position'] ?? []

    // Compute contiguous Long and Short periods from position data.
    // Threshold 0.5: catches +1 as Long, -1 as Short; treats 0 as Flat (no band).
    // Values stored as strings: ECharts category axis matches markArea xAxis values
    // by string equality internally, so String() is required for bands to render.
    const longPeriods: [string, string][] = []
    const shortPeriods: [string, string][] = []

    let periodStart: string | null = null
    let periodType: 'long' | 'short' | null = null

    for (let i = 0; i < posValues.length; i++) {
      const v = Number(posValues[i])
      const currentType = v > 0.5 ? 'long' : v < -0.5 ? 'short' : null

      if (currentType !== periodType) {
        if (periodType !== null && periodStart !== null) {
          const endIdx = Math.max(0, i - 1)
          if (periodType === 'long') longPeriods.push([periodStart, String(position.index[endIdx])])
          if (periodType === 'short') shortPeriods.push([periodStart, String(position.index[endIdx])])
        }
        periodStart = currentType !== null ? String(position.index[i]) : null
        periodType = currentType
      }
    }
    // Close final open period
    if (periodType !== null && periodStart !== null) {
      const lastIdx = position.index.length - 1
      if (periodType === 'long') longPeriods.push([periodStart, String(position.index[lastIdx])])
      if (periodType === 'short') shortPeriods.push([periodStart, String(position.index[lastIdx])])
    }

    // Rebuild band colors at 8% opacity — bands are background context only,
    // candlesticks must remain the primary visual element.
    const toRgba = (color: string, alpha: number): string => {
      const match = color.match(/[\d.]+/g)
      if (!match || match.length < 3) return color
      return `rgba(${match[0]}, ${match[1]}, ${match[2]}, ${alpha})`
    }
    const longColor = toRgba(theme.gainFill, 0.08)
    const shortColor = toRgba(theme.lossFill, 0.08)

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: [
        { left: 60, right: 24, top: '2%',  height: '58%' },  // price pane
        { left: 60, right: 24, top: '63%', bottom: 36 },      // signal pane (now bottom)
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          zoomOnMouseWheel: 'ctrl',
          moveOnMouseWheel: false,
          zoomLock: false,
        },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          bottom: 10,
          height: 18,
        },
      ],
      xAxis: [
        {
          // xAxis[0] — price pane — hidden labels (not bottom pane)
          gridIndex: 0,
          type: 'category' as const,
          data: index,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisPointer: {
            label: { formatter: (p: { value: number }) => fmtDate(p.value) },
          },
        },
        {
          // xAxis[1] — signal pane — now the bottom pane, shows date labels
          gridIndex: 1,
          type: 'category' as const,
          data: raw.index,
          axisLabel: {
            show: true,
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
            margin: 8,
            formatter: (v: number | string) => {
              const ms = typeof v === 'string' ? Number(v) : v
              return fmtDate(ms)
            },
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisPointer: {
            label: { formatter: (p: { value: number }) => fmtDate(p.value) },
          },
        },
      ],
      yAxis: [
        {
          // yAxis[0] — price pane
          gridIndex: 0,
          scale: true,
          boundaryGap: ['1%', '1%'],
          min: (value: { min: number }) => Math.floor(value.min * 0.99),
          max: (value: { max: number }) => Math.ceil(value.max * 1.01),
          axisLabel: {
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor } },
        },
        {
          // yAxis[1] — signal pane
          // Callbacks clamp axis exactly to data extent — no extra padding or unlabeled ticks.
          gridIndex: 1,
          min: (value: { min: number }) => Math.floor(value.min),
          max: (value: { max: number }) => Math.ceil(value.max),
          splitNumber: 3,
          axisLabel: {
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 11,
            formatter: (v: number) => Number(v).toFixed(2),
            showMinLabel: false,
            showMaxLabel: false,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor } },
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
        formatter: (params: unknown) => {
          const items = (Array.isArray(params) ? params : [params]) as Array<{
            seriesType?: string
            seriesName?: string
            name?: string | number
            axisValue?: string | number
            value?: unknown
            data?: unknown
            marker?: string
          }>
          const axisRaw = items[0]?.axisValue ?? items[0]?.name
          const axisMs = typeof axisRaw === 'number' ? axisRaw : Number(axisRaw)
          const dateLabel = Number.isFinite(axisMs) ? fmtDate(axisMs) : String(axisRaw ?? '')

          const candleItem = items.find((p) => p.seriesType === 'candlestick')
          const signalItem = items.find((p) => p.seriesName === 'Signal')

          const lines: string[] = [dateLabel]

          if (candleItem) {
            const rawVal = (Array.isArray(candleItem.value) ? candleItem.value : candleItem.data) as number[] | undefined
            if (rawVal && rawVal.length >= 4) {
              const prices = rawVal.length >= 5 ? rawVal.slice(1, 5) : rawVal.slice(0, 4)
              const [o, c, l, h] = prices
              lines.push(
                `O: ${Number(o).toFixed(2)}`,
                `C: ${Number(c).toFixed(2)}`,
                `L: ${Number(l).toFixed(2)}`,
                `H: ${Number(h).toFixed(2)}`,
              )
            }
          }

          if (signalItem) {
            const sv = Array.isArray(signalItem.value)
              ? (signalItem.value as unknown[])[1]
              : signalItem.value
            if (sv != null) {
              lines.push(`${signalItem.marker ?? ''}Signal: ${Number(sv).toFixed(2)}`)
            }
          }

          return lines.join('<br/>')
        },
      },
      series: [
        {
          // Candlestick — price pane, no background tints
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
          // Signal line — same Long/Short bands mirrored on signal pane
          type: 'line' as const,
          name: 'Signal',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: rawValues,
          connectNulls: false, // ← mandatory: gaps, never interpolate nulls
          lineStyle: { color: theme.amber, width: 1.5 },
          itemStyle: { color: theme.amber },
          symbol: 'none',
          endLabel: { show: false },
          markLine: {
            silent: true,
            data: [{ yAxis: 0, label: { show: false } }],
            lineStyle: { color: theme.secondaryText, type: 'dashed' },
          },
          markArea: {
            silent: true,
            data: [
              ...longPeriods.map(([start, end]) => [
                { xAxis: start, itemStyle: { color: longColor } },
                { xAxis: end },
              ]),
              ...shortPeriods.map(([start, end]) => [
                { xAxis: start, itemStyle: { color: shortColor } },
                { xAxis: end },
              ]),
            ],
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

  // Pinch (ctrlKey=true) → let ECharts zoom. Normal scroll → page scrolls.
  useEffect(() => {
    const el = divRef.current
    if (!el) return
    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey) {
        e.stopPropagation()
      }
    }
    el.addEventListener('wheel', handleWheel, { passive: true })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [])

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
  asset: _asset,
}: SignalOverlayChartProps) {
  const theme = useChartTheme()

  // Inline legend: swatches rendered on the right side of the header row
  // via ChartFrame's `actions` prop (Panel places actions after justify-between)
  const legend = (
    <div className="flex items-center gap-3 text-xs text-text-secondary font-mono">
      <span className="flex items-center gap-1">
        <span className="inline-block h-3 w-4 rounded-sm bg-gain-fill opacity-70" />
        Long
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block h-3 w-4 rounded-sm bg-loss-fill opacity-70" />
        Short
      </span>
    </div>
  )

  return (
    <ChartFrame
      title={title ?? 'Signal'}
      actions={legend}
      height={height}
      loading={loading}
      error={error}
      syncGroup={syncGroup}
    >
      <SignalOverlayChartInner ohlcv={ohlcv} raw={raw} position={position} theme={theme} />
    </ChartFrame>
  )
}
