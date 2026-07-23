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
  showRegimeBands?: boolean // default: true
}

interface InnerProps {
  snapshots: TermStructureSnapshotSummary[]
  theme: EChartsTheme
  showRegimeBands: boolean
}

function buildRegimeBands(
  snapshots: TermStructureSnapshotSummary[],
  amberHex: string,
  gainHex: string,
  gridIndex: number
) {
  if (snapshots.length < 2) return []

  const bands: Array<{ start: number; end: number; regime: string }> = []
  let currentRegime = snapshots[0].regime
  let startIdx = 0

  for (let i = 1; i <= snapshots.length; i++) {
    const snap = snapshots[i]
    if (!snap || snap.regime !== currentRegime) {
      bands.push({
        start: new Date(snapshots[startIdx].observation_date).getTime(),
        end: new Date(snapshots[Math.min(i, snapshots.length - 1)].observation_date).getTime(),
        regime: currentRegime,
      })
      if (snap) {
        currentRegime = snap.regime
        startIdx = i
      }
    }
  }

  const toMarkAreaData = (bs: typeof bands) => bs.map((b) => [{ xAxis: b.start }, { xAxis: b.end }])

  return [
    {
      type: 'line' as const,
      data: [] as never[],
      xAxisIndex: gridIndex,
      yAxisIndex: gridIndex,
      markArea: {
        silent: true,
        itemStyle: { color: amberHex + '26' }, // ~15% opacity — contango
        data: toMarkAreaData(bands.filter((b) => b.regime === 'contango')),
      },
    },
    {
      type: 'line' as const,
      data: [] as never[],
      xAxisIndex: gridIndex,
      yAxisIndex: gridIndex,
      markArea: {
        silent: true,
        itemStyle: { color: gainHex + '1F' }, // ~12% opacity — backwardation
        data: toMarkAreaData(bands.filter((b) => b.regime === 'backwardation')),
      },
    },
  ]
}

function TermStructureHistoryChartInner({ snapshots, theme, showRegimeBands }: InnerProps) {
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
        { top: '55%', left: 64, right: 16, bottom: 60 },
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
          bottom: 8,
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
        formatter: (params: unknown) => {
          const items = (Array.isArray(params) ? params : [params]) as Array<{
            seriesName?: string
            value?: unknown
            axisValue?: string | number
            marker?: string
          }>
          const axisRaw = items[0]?.axisValue
          const axisMs = typeof axisRaw === 'number' ? axisRaw : Number(axisRaw)
          const dateLabel = Number.isFinite(axisMs)
            ? new Date(axisMs).toISOString().slice(0, 10)
            : String(axisRaw ?? '')
          const lines = items
            .filter((p) => p.seriesName === 'Slope %/yr' || p.seriesName === 'Roll Yield %/yr')
            .map((p) => {
              const marker = p.marker ?? ''
              let v: unknown = p.value
              if (Array.isArray(p.value)) {
                const arr = p.value as unknown[]
                v = arr[arr.length - 1]
              }
              if (v == null || (typeof v !== 'number' && typeof v !== 'string')) {
                return `${marker}${p.seriesName}: —`
              }
              const num = Number(v)
              if (!Number.isFinite(num)) return `${marker}${p.seriesName}: —`
              // Values are decimal fractions (0.0493 → 4.93%/yr)
              return `${marker}${p.seriesName}: ${(num * 100).toFixed(2)}%/yr`
            })
          return [dateLabel, ...lines].join('<br/>')
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
        ...(showRegimeBands
          ? [
              ...buildRegimeBands(snapshots, theme.amber, theme.gain, 0),
              ...buildRegimeBands(snapshots, theme.amber, theme.gain, 1),
            ]
          : []),
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [snapshots, theme, showRegimeBands, ctx])

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
  showRegimeBands = true,
}: TermStructureHistoryChartProps) {
  const theme = useChartTheme()
  const isEmpty = !loading && !error && snapshots.length === 0

  return (
    <>
      <ChartFrame
        height={height}
        title={title}
        loading={loading}
        error={error}
        empty={isEmpty ? { message: 'No history data available for this asset.' } : undefined}
        syncGroup={syncGroup}
        onRetry={onRetry}
      >
        {!isEmpty && (
          <TermStructureHistoryChartInner
            snapshots={snapshots}
            theme={theme}
            showRegimeBands={showRegimeBands}
          />
        )}
      </ChartFrame>
      {showRegimeBands !== false && snapshots.length >= 2 && (
        <div className="mt-2 flex items-center gap-4 px-2 text-xs text-text-secondary">
          <span className="gap-1.5 flex items-center">
            <span className="inline-block h-3 w-6 rounded-sm bg-accent-fill opacity-60" />
            Contango
          </span>
          <span className="gap-1.5 flex items-center">
            <span className="inline-block h-3 w-6 rounded-sm bg-gain-fill opacity-50" />
            Backwardation
          </span>
        </div>
      )}
    </>
  )
}
