import { useEffect, useRef } from 'react'
import type { EChartsOption } from 'echarts'
import type { ApiClientError } from '@/api/client'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme } from '@/lib/chart-theme'
import { displayName } from '@/lib/commodity'

interface CorrelationHeatmapChartProps {
  correlationMatrix: Record<string, Record<string, number>>
  assets: string[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
}

function CorrelationHeatmapInner({
  correlationMatrix,
  assets,
}: Pick<CorrelationHeatmapChartProps, 'correlationMatrix' | 'assets'>) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const { onChartReady } = useChartFrame() ?? {}
  const theme = useChartTheme()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    onChartReady?.(chart)

    const axisLabels = assets.map((a) => displayName(a))

    const data: [number, number, number][] = []
    assets.forEach((assetRow, ri) => {
      assets.forEach((assetCol, ci) => {
        const val = correlationMatrix[assetRow]?.[assetCol] ?? 0
        data.push([ci, ri, parseFloat(val.toFixed(3))])
      })
    })

    const option: EChartsOption = {
      grid: { left: 80, right: 20, bottom: 60, top: '5%' },
      xAxis: {
        type: 'category',
        data: axisLabels,
        axisLabel: {
          rotate: 45,
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitArea: { show: true },
      },
      yAxis: {
        type: 'category',
        data: axisLabels,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitArea: { show: true },
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: {
          // Resolve at option-build time (browser): ECharts rejects var(--x) strings.
          color: [
            // eslint-disable-next-line no-restricted-syntax -- ECharts needs resolved hex; fallback only if CSS token missing
            resolveCssVar('--text-loss', '#ef4444'),
            // eslint-disable-next-line no-restricted-syntax -- ECharts needs resolved hex; fallback only if CSS token missing
            resolveCssVar('--bg-raised', '#1e2a3a'),
            // eslint-disable-next-line no-restricted-syntax -- ECharts needs resolved hex; fallback only if CSS token missing
            resolveCssVar('--text-gain', '#22c55e'),
          ],
        },
        textStyle: { color: theme.secondaryText, fontSize: 10 },
        text: ['1.0', '-1.0'],
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: {
            show: true,
            formatter: (params: { value: unknown }) => {
              const v = (params.value as [number, number, number])[2]
              return v.toFixed(2)
            },
            fontSize: 10,
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
          },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
          },
        },
      ],
      tooltip: {
        trigger: 'item',
        formatter: (params: unknown) => {
          const { value } = params as { value: unknown }
          const [xi, yi, val] = value as [number, number, number]
          return `${axisLabels[yi]} / ${axisLabels[xi]}: ${val.toFixed(3)}`
        },
        backgroundColor: theme.tooltip.backgroundColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
        },
      },
    }

    chart.setOption(option)

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
      chartRef.current = null
    }
  }, [assets, correlationMatrix, onChartReady, theme])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function CorrelationHeatmapChart({
  correlationMatrix,
  assets,
  title = 'Strategy Return Correlations',
  height = 360,
  loading,
  error,
  empty,
}: CorrelationHeatmapChartProps) {
  const isEmpty = !correlationMatrix || Object.keys(correlationMatrix).length === 0

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      empty={isEmpty ? (empty ?? { message: 'No correlation data' }) : undefined}
    >
      <CorrelationHeatmapInner correlationMatrix={correlationMatrix} assets={assets} />
    </ChartFrame>
  )
}
