/**
 * PortfolioRollingCorrelationChart — rolling correlation lines for the top-N
 * most correlated asset pairs (ranked by absolute static pairwise correlation).
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   PortfolioRollingCorrelationChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                                 — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Presentation only: consumes pre-computed rolling-correlation series + the
 * static correlation matrix from cached portfolio data. Every pair is sorted
 * before lookup so it hits the upper-triangle key ordering.
 *
 * CRITICAL:
 *   - connectNulls: false on ALL series (gaps, never interpolation)
 *   - yAxis fixed to [-1, 1] — correlation domain
 *
 * Does NOT: fetch data, compute correlations, store window/zoom state.
 */
import { useEffect, useRef } from 'react'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { displayName } from '@/lib/commodity'
import { fmtDate } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']
type RollingCorrSeries = components['schemas']['RollingCorrSeries']

// Wire format is RollingCorrSeries ({ asset_a, asset_b, data }); test fixtures
// pass a bare ColumnarSeries. normalizeSeries() resolves either shape.
type RollingEntry = RollingCorrSeries | ColumnarSeries

interface PortfolioRollingCorrelationChartProps {
  rollingCorrelations: Record<string, Record<string, RollingEntry>>
  correlationMatrix: Record<string, Record<string, number>>
  windowDays: 63 | 126
  topN?: number
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

function getTopPairs(
  matrix: Record<string, Record<string, number>>,
  n: number
): [string, string][] {
  const assets = Object.keys(matrix).sort()
  const pairs: [string, string, number][] = []
  assets.forEach((a, i) => {
    assets.slice(i + 1).forEach((b) => {
      pairs.push([a, b, Math.abs(matrix[a]?.[b] ?? 0)])
    })
  })
  return pairs
    .sort((x, y) => y[2] - x[2])
    .slice(0, n)
    .map(([a, b]) => [a, b] as [string, string])
}

function normalizeSeries(entry: RollingEntry | undefined): ColumnarSeries | undefined {
  if (!entry) return undefined
  return 'data' in entry ? entry.data : entry
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle, accesses ChartFrameContext
// ---------------------------------------------------------------------------

interface PortfolioRollingCorrelationChartInnerProps {
  rollingCorrelations: Record<string, Record<string, RollingEntry>>
  topPairs: [string, string][]
  windowDays: 63 | 126
  theme: EChartsTheme
}

function PortfolioRollingCorrelationChartInner({
  rollingCorrelations,
  topPairs,
  windowDays,
  theme,
}: PortfolioRollingCorrelationChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const series = topPairs.map(([a, b], i) => {
      // ALWAYS sort for upper-triangle lookup (keys are asset_a < asset_b).
      const [lo, hi] = [a, b].sort()
      const rolling = normalizeSeries(rollingCorrelations?.[lo]?.[hi])
      const values = rolling?.columns?.value ?? []
      const data = (rolling?.index ?? []).map(
        (t, idx) => [t, values[idx] ?? null] as [number, number | null]
      )
      return {
        name: `${displayName(lo)} / ${displayName(hi)}`,
        type: 'line' as const,
        data,
        connectNulls: false,
        symbol: 'none',
        lineStyle: { color: theme.seriesPalette[i % 6], width: 1.5 },
        itemStyle: { color: theme.seriesPalette[i % 6] },
        // Zero-correlation reference line attached to the first series only.
        ...(i === 0
          ? {
              markLine: {
                silent: true,
                symbol: 'none',
                data: [{ yAxis: 0 }],
                lineStyle: { type: 'dashed' as const, color: theme.gridlineColor },
                label: { show: false },
              },
            }
          : {}),
      }
    })

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      title: {
        text: `${windowDays}-day rolling correlation`,
        left: 8,
        top: 4,
        textStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          fontWeight: 'normal' as const,
        },
      },
      grid: { left: 52, right: 16, top: 40, bottom: 60 },
      xAxis: {
        type: 'time' as const,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (v: number) => fmtDate(v),
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value' as const,
        min: -1,
        max: 1,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (v: number) => v.toFixed(2),
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      tooltip: {
        trigger: 'axis' as const,
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
            value?: number | [number, number | null]
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
      legend: {
        type: 'scroll' as const,
        bottom: 0,
        textStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
      },
      dataZoom: [{ type: 'inside' as const, xAxisIndex: 0 }],
      series,
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [rollingCorrelations, topPairs, windowDays, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function PortfolioRollingCorrelationChart({
  rollingCorrelations,
  correlationMatrix,
  windowDays,
  topN = 5,
  title,
  height = 280,
  loading,
  error,
  empty,
}: PortfolioRollingCorrelationChartProps) {
  const theme = useChartTheme()
  const topPairs = getTopPairs(correlationMatrix, topN)
  const isEmpty = topPairs.length === 0

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      empty={isEmpty ? (empty ?? { message: 'No rolling correlation data available.' }) : undefined}
    >
      <PortfolioRollingCorrelationChartInner
        rollingCorrelations={rollingCorrelations}
        topPairs={topPairs}
        windowDays={windowDays}
        theme={theme}
      />
    </ChartFrame>
  )
}
