import { useEffect, useRef } from 'react'
import type { AssetSnapshotWithLabel } from '@/api/hooks/useCurveSnapshots'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'

type CurvePointResponse = components['schemas']['CurvePointResponse']

interface CurveComparisonChartProps {
  snapshots: AssetSnapshotWithLabel[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
  syncGroup?: string
}

interface CurveComparisonChartInnerProps {
  snapshots: AssetSnapshotWithLabel[]
  theme: EChartsTheme
}

function normalizeToFrontPct(
  points: CurvePointResponse[],
  frontPrice: number | null
): [number, number][] {
  if (!frontPrice || frontPrice <= 0) return []
  return points.map((point) => [point.days_to_delivery, (point.close / frontPrice - 1) * 100])
}

function CurveComparisonChartInner({ snapshots, theme }: CurveComparisonChartInnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current) return

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const series = snapshots.map((snapshot, index) => ({
      type: 'line' as const,
      name: snapshot.label,
      data: normalizeToFrontPct(snapshot.snapshot.points, snapshot.snapshot.front_price),
      color: theme.seriesPalette[index % 6],
      lineStyle: {
        color: theme.seriesPalette[index % 6],
        width: 2,
      },
      itemStyle: { color: theme.seriesPalette[index % 6] },
      symbol: 'circle',
      symbolSize: 7,
      connectNulls: false,
      ...(index === 0
        ? {
            markLine: {
              silent: true,
              symbol: 'none',
              label: { show: false },
              lineStyle: {
                color: theme.secondaryText,
                type: 'dashed' as const,
              },
              data: [{ yAxis: 0 }],
            },
          }
        : {}),
    }))

    chart.setOption({
      backgroundColor: 'transparent',
      grid: { left: 60, right: 16, top: 24, bottom: 58 },
      xAxis: {
        type: 'value',
        name: 'Days to delivery',
        nameLocation: 'end',
        min: 0,
        nameTextStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (value: number) => `${value}d`,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      yAxis: {
        type: 'value',
        name: '% from front',
        nameLocation: 'end',
        min: null,
        nameTextStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      legend: {
        bottom: 0,
        type: 'scroll',
        textStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.tooltip.textStyle.fontFamily,
          fontSize: theme.tooltip.textStyle.fontSize,
        },
        formatter: (params: { seriesName: string; value: [number, number] }) => {
          const [days, normalized] = params.value
          return `${params.seriesName}<br/>${days}d: ${
            normalized >= 0 ? '+' : ''
          }${normalized.toFixed(2)}%`
        },
      },
      dataZoom: [{ type: 'inside', xAxisIndex: 0 }],
      series,
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [snapshots, theme, ctx])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export const CurveComparisonChart = ({
  snapshots,
  title,
  height = 320,
  loading,
  error,
  empty,
  syncGroup,
}: CurveComparisonChartProps) => {
  const theme = useChartTheme()

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      empty={empty}
      syncGroup={syncGroup}
    >
      <CurveComparisonChartInner snapshots={snapshots} theme={theme} />
    </ChartFrame>
  )
}
