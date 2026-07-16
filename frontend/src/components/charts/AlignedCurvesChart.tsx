/**
 * AlignedCurvesChart — multi-line normalized equity chart for run comparison.
 *
 * Architecture:
 *   AlignedCurvesChart (outer) — renders ChartFrame, calls useChartTheme()
 *   AlignedCurvesChartInner   — accesses ChartFrameCtx, owns the ECharts lifecycle
 *
 * CRITICAL: connectNulls: false on ALL series — gaps, never interpolation.
 *
 * Does NOT: fetch data, compute alignment.
 */
import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

interface AlignedRunSeriesWithLabel {
  runId: string
  label: string
  equityNormalized: ColumnarSeries
}

interface AlignedCurvesChartInnerProps {
  series: AlignedRunSeriesWithLabel[]
  intersectionFrom?: string | null
  intersectionTo?: string | null
  theme: EChartsTheme
}

interface AlignedCurvesChartProps {
  series: AlignedRunSeriesWithLabel[]
  intersectionFrom?: string | null
  intersectionTo?: string | null
  mixedAssets?: boolean
  title?: string
  height?: number | string
  loading?: boolean
  error?: Error | null
  className?: string
}

function AlignedCurvesChartInner({
  series,
  intersectionFrom,
  intersectionTo,
  theme,
}: AlignedCurvesChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    // Use first series index as shared x-axis (aligned series share the same index)
    const index = series[0]?.equityNormalized.index ?? []

    const echartsSeries = series.map((item, idx) => {
      const cols = item.equityNormalized.columns as Record<string, (number | null)[]>
      const values = cols['value'] ?? []
      const color = theme.seriesPalette[idx % theme.seriesPalette.length]
      return {
        type: 'line' as const,
        name: item.label,
        data: values,
        connectNulls: false,
        symbol: 'none',
        lineStyle: { color, width: 1.5 },
        itemStyle: { color },
        markLine:
          idx === 0
            ? {
                silent: true,
                data: [{ yAxis: 0 }],
                lineStyle: { type: 'dashed' as const, width: 1 },
              }
            : undefined,
      }
    })

    // Optional intersection window shading when both bounds are provided
    const markArea =
      intersectionFrom && intersectionTo
        ? {
            silent: true,
            itemStyle: { color: 'transparent' },
            data: [
              [
                { xAxis: Date.parse(intersectionFrom) },
                { xAxis: Date.parse(intersectionTo) },
              ],
            ],
          }
        : undefined

    if (markArea && echartsSeries.length > 0) {
      const first = echartsSeries[0] as typeof echartsSeries[0] & { markArea?: unknown }
      first.markArea = markArea
    }

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 60, right: 16, top: '12%', bottom: '18%' },
      legend: {
        top: 0,
        textStyle: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
      },
      xAxis: {
        type: 'category' as const,
        data: index,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
      },
      yAxis: {
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (v: number) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      axisPointer: {
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
      dataZoom: [
        { type: 'slider' as const, bottom: 0, xAxisIndex: [0], height: 20 },
        { type: 'inside' as const, xAxisIndex: [0] },
      ],
      series: echartsSeries,
    })

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [series, intersectionFrom, intersectionTo, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function AlignedCurvesChart({
  series,
  intersectionFrom,
  intersectionTo,
  mixedAssets,
  title,
  height = 360,
  loading,
  error,
  className,
}: AlignedCurvesChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      className={className}
    >
      <div className={cn('flex h-full flex-col')}>
        {mixedAssets && (
          <div className="mb-2 flex items-center gap-3 rounded-sm border-l-[3px] border-warn bg-bg-raised px-4 py-2">
            <AlertTriangle size={14} strokeWidth={1.75} className="shrink-0 text-warn" />
            <span className="text-xs text-text-primary">
              Comparing across different assets — returns reflect both signal and commodity
              price differences.
            </span>
          </div>
        )}
        <div className="min-h-0 flex-1">
          <AlignedCurvesChartInner
            series={series}
            intersectionFrom={intersectionFrom}
            intersectionTo={intersectionTo}
            theme={theme}
          />
        </div>
      </div>
    </ChartFrame>
  )
}
