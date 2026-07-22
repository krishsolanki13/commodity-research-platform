/**
 * PriceChart — OHLCV candlestick/line chart with volume pane, indicator
 * overlays, and trade entry/exit markers.
 *
 * Architecture:
 *   PriceChart (outer) — renders ChartFrame, calls useChartTheme()
 *   PriceChartInner   — accesses ChartFrameCtx, owns the ECharts lifecycle
 *
 * CRITICAL constraints:
 *   - Price yAxis: min: null (NEVER min: 0 — WTI went to -$37.63 in 2020)
 *   - All line series: connectNulls: false (gaps, never interpolation)
 *   - Candlestick data order: [open, close, low, high] per ECharts convention
 *
 * Does NOT: fetch data, store filter/zoom state, compute indicators.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { fmtDate } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

// ---------------------------------------------------------------------------
// Types — exported so F5+ screens can construct these without re-defining them.
// Migration trigger: if a second chart imports either type, extract both to
// src/components/charts/types.ts at that point.
// ---------------------------------------------------------------------------

type ColumnarSeries = components['schemas']['ColumnarSeries']
type FeatureSpecResponse = components['schemas']['FeatureSpecResponse']

export interface OverlayData {
  spec: FeatureSpecResponse
  values: (number | null)[]
}

export interface DateMarker {
  date: number // epoch ms
  type: 'entry' | 'exit' | 'event'
  label?: string
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PriceChartInnerProps {
  ohlcv: ColumnarSeries
  overlays: OverlayData[]
  markers: DateMarker[]
  volume: boolean
  style: 'candle' | 'line'
  theme: EChartsTheme
}

interface PriceChartProps {
  ohlcv: ColumnarSeries
  overlays?: OverlayData[]
  markers?: DateMarker[]
  volume?: boolean
  style?: 'candle' | 'line'
  // ChartFrame passthrough
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
  syncGroup?: string
  onRetry?: () => void
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle, accesses ChartFrameContext
// ---------------------------------------------------------------------------

function PriceChartInner({ ohlcv, overlays, markers, volume, style, theme }: PriceChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const cols = ohlcv.columns as Record<string, (number | null)[]>
    const open = cols['open'] ?? []
    const high = cols['high'] ?? []
    const low = cols['low'] ?? []
    const close = cols['close'] ?? []
    const vol = cols['volume'] ?? []
    const index = ohlcv.index

    // Candlestick: filter bars where any OHLC value is null
    // ECharts candlestick data order: [open, close, low, high]
    const candleData = index.map((_t, i) => {
      if (open[i] == null || close[i] == null || low[i] == null || high[i] == null) {
        return null
      }
      return [open[i], close[i], low[i], high[i]]
    })

    const showVolume = volume && vol.length > 0

    const grids = showVolume
      ? [
          { left: 60, right: 16, top: '5%', height: '72%' },
          { left: 60, right: 16, bottom: '6%', height: '14%' },
        ]
      : [{ left: 60, right: 16, top: '5%', bottom: '6%' }]

    const xAxes = showVolume
      ? [
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
            data: index,
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
            data: index,
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
              formatter: (value: number) => fmtDate(value),
            },
          },
        ]

    // CRITICAL: min: null on price axis — NEVER min: 0
    // WTI settled at -$37.63 on 2020-04-20. min: 0 would silently corrupt that data.
    const yAxes = showVolume
      ? [
          {
            gridIndex: 0,
            min: null, // ← auto-scale: required for negative prices
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
            },
            splitLine: { lineStyle: { color: theme.gridlineColor } },
          },
          {
            gridIndex: 1,
            min: 0, // volume is always >= 0
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
              formatter: (v: number) =>
                v >= 1000000
                  ? `${(v / 1000000).toFixed(1)}M`
                  : v >= 1000
                    ? `${(v / 1000).toFixed(0)}k`
                    : String(v),
            },
            splitLine: { show: false },
            splitNumber: 2,
          },
        ]
      : [
          {
            min: null, // ← auto-scale: required for negative prices
            axisLabel: {
              color: theme.secondaryText,
              fontFamily: theme.monoFont,
              fontSize: 11,
            },
            splitLine: { lineStyle: { color: theme.gridlineColor } },
          },
        ]

    const priceSeries =
      style === 'candle'
        ? {
            type: 'candlestick' as const,
            xAxisIndex: 0,
            yAxisIndex: 0,
            data: candleData,
            connectNulls: false, // ← null gap policy: gaps, not interpolation
            itemStyle: {
              color: theme.gain, // up candle body
              color0: theme.loss, // down candle body
              borderColor: theme.gain,
              borderColor0: theme.loss,
            },
          }
        : {
            type: 'line' as const,
            xAxisIndex: 0,
            yAxisIndex: 0,
            data: index.map((_t, i) => close[i] ?? null),
            connectNulls: false, // ← null gap policy
            lineStyle: { color: theme.amber, width: 1.5 },
            itemStyle: { color: theme.amber },
            symbol: 'none',
          }

    const volumeSeries = showVolume
      ? [
          {
            type: 'bar' as const,
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: index.map((_t, i) => ({
              value: vol[i],
              itemStyle: {
                color:
                  close[i] != null && open[i] != null && close[i] >= open[i]
                    ? `${theme.gain}80`
                    : `${theme.loss}80`,
              },
            })),
          },
        ]
      : []

    const overlaySeries = overlays.map((overlay, idx) => ({
      type: 'line' as const,
      name: overlay.spec.column_name,
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: overlay.values,
      connectNulls: false, // ← null gap policy
      lineStyle: { color: theme.seriesPalette[idx % 6], width: 1 },
      itemStyle: { color: theme.seriesPalette[idx % 6] },
      symbol: 'none',
    }))

    const dataZoom = [
      {
        type: 'slider' as const,
        bottom: 0,
        xAxisIndex: showVolume ? [0, 1] : [0],
        height: 20,
      },
      {
        type: 'inside' as const,
        xAxisIndex: showVolume ? [0, 1] : [0],
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
          const lines = items.map((p) => {
            const marker = p.marker ?? ''
            if (p.seriesType === 'candlestick') {
              // ECharts candlestick value: [open, close, low, high] (or [idx, open, close, low, high])
              const raw = (Array.isArray(p.value) ? p.value : p.data) as number[] | undefined
              if (!raw || raw.length < 4) return `${marker}—`
              const prices = raw.length >= 5 ? raw.slice(1, 5) : raw.slice(0, 4)
              const [open, close, low, high] = prices
              return [
                `${marker}O: ${Number(open).toFixed(2)}`,
                `C: ${Number(close).toFixed(2)}`,
                `L: ${Number(low).toFixed(2)}`,
                `H: ${Number(high).toFixed(2)}`,
              ].join('<br/>')
            }
            let v: unknown = p.value
            if (Array.isArray(p.value)) {
              const arr = p.value as unknown[]
              v = arr[arr.length - 1]
            }
            if (typeof v !== 'number' && typeof v !== 'string') {
              return `${marker}${p.seriesName ?? ''}: —`
            }
            const num = Number(v)
            const formatted = Number.isFinite(num) ? num.toFixed(2) : v
            return `${marker}${p.seriesName ?? ''}: ${formatted}`
          })
          return [dateLabel, ...lines].join('<br/>')
        },
      },
      dataZoom,
      series: [priceSeries, ...volumeSeries, ...overlaySeries],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [ohlcv, overlays, markers, volume, style, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function PriceChart({
  ohlcv,
  overlays = [],
  markers = [],
  volume = true,
  style = 'candle',
  title,
  height = 300,
  loading,
  error,
  empty,
  syncGroup,
  onRetry,
}: PriceChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      empty={empty}
      syncGroup={syncGroup}
      onRetry={onRetry}
    >
      <PriceChartInner
        ohlcv={ohlcv}
        overlays={overlays}
        markers={markers}
        volume={volume}
        style={style}
        theme={theme}
      />
    </ChartFrame>
  )
}
