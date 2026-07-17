/**
 * FuturesCurveChart — forward curve bar+line overlay for a single observation.
 *
 * Architecture (same as PriceChart):
 *   FuturesCurveChart (outer) — ChartFrame chrome + useChartTheme()
 *   FuturesCurveChartInner   — owns ECharts lifecycle via ChartFrame context
 *
 * CRITICAL:
 *   - xAxis type: 'category' (tickers, not time)
 *   - yAxis min: null (never min: 0 — price can be negative)
 *   - line series connectNulls: false
 *
 * Does NOT: fetch data, call TermStructureAnalyzer.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { fmt } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type CurvePointResponse = components['schemas']['CurvePointResponse']
type Regime = 'contango' | 'backwardation' | 'flat' | null

export interface FuturesCurveChartProps {
  points: CurvePointResponse[]
  regime: Regime
  asset: string
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
  onRetry?: () => void
}

interface InnerProps {
  points: CurvePointResponse[]
  regime: Regime
  asset: string
  theme: EChartsTheme
}

function FuturesCurveChartInner({ points, regime, asset, theme }: InnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const barColor = regime === 'backwardation' ? theme.gainFill : theme.gridlineColor
    const barBorderColor = regime === 'backwardation' ? theme.gain : theme.secondaryText

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { top: 24, right: 16, bottom: 40, left: 72, containLabel: false },
      xAxis: [
        {
          type: 'category',
          data: points.map((p) => p.ticker),
          axisLabel: {
            color: theme.secondaryText,
            rotate: points.length > 4 ? 45 : 0,
            fontSize: 11,
            fontFamily: theme.monoFont,
          },
          axisLine: { lineStyle: { color: theme.gridlineColor } },
          axisTick: { lineStyle: { color: theme.gridlineColor } },
        },
      ],
      yAxis: [
        {
          type: 'value',
          min: null,
          axisLabel: {
            color: theme.secondaryText,
            formatter: (v: number) => fmt.price(v, asset),
            fontSize: 10,
            fontFamily: theme.monoFont,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor, opacity: 0.4 } },
        },
      ],
      tooltip: {
        trigger: 'item',
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
          fontSize: 12,
        },
        formatter: (params: unknown) => {
          const p = params as {
            name?: string
            value?: number
            dataIndex?: number
          }
          const name = String(p.name ?? '')
          const value = Number(p.value ?? 0)
          const idx = Number(p.dataIndex ?? 0)
          const point = points[idx]
          return [
            `<strong>${name}</strong>`,
            fmt.price(value, asset),
            point ? `${point.days_to_delivery} days to delivery` : '',
          ]
            .filter(Boolean)
            .join('<br/>')
        },
      },
      series: [
        {
          type: 'bar',
          data: points.map((p) => p.close),
          barMaxWidth: 40,
          itemStyle: {
            color: barColor,
            borderColor: barBorderColor,
            borderWidth: 1,
          },
        },
        {
          type: 'line',
          data: points.map((p) => p.close),
          connectNulls: false,
          lineStyle: { color: theme.amber, width: 2 },
          itemStyle: { color: theme.amber },
          symbol: 'circle',
          symbolSize: 6,
          z: 10,
        },
      ],
    })

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [points, regime, asset, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function FuturesCurveChart({
  points,
  regime,
  asset,
  title,
  height = 300,
  loading,
  error,
  empty,
  onRetry,
}: FuturesCurveChartProps) {
  const theme = useChartTheme()
  const isEmpty = !loading && !error && points.length === 0

  return (
    <ChartFrame
      height={height}
      title={title}
      loading={loading}
      error={error}
      empty={isEmpty ? (empty ?? { message: 'No contract data available.' }) : undefined}
      onRetry={onRetry}
    >
      {!isEmpty && (
        <FuturesCurveChartInner points={points} regime={regime} asset={asset} theme={theme} />
      )}
    </ChartFrame>
  )
}
