/**
 * ReturnHistogram — daily-return distribution chart.
 *
 * Architecture (matches PriceChart):
 *   ReturnHistogram (outer) — renders ChartFrame, calls useChartTheme()
 *   ReturnHistogramInner   — accesses ChartFrameCtx, owns the ECharts lifecycle
 *
 * Does NOT: fetch data, compute returns from prices.
 */
import { useEffect, useMemo, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { ApiClientError } from '@/api/client'

interface ReturnHistogramInnerProps {
  values: number[]
  bins: number
  markers: Array<'mean' | 'median'>
  theme: EChartsTheme
}

interface ReturnHistogramProps {
  values: number[]
  bins?: number
  markers?: Array<'mean' | 'median'>
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  syncGroup?: string
}

function ReturnHistogramInner({ values, bins, markers, theme }: ReturnHistogramInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  const { binData, meanVal, medianVal } = useMemo(() => {
    if (values.length < 2) return { binData: [] as [string, number][], meanVal: 0, medianVal: 0 }

    const min = Math.min(...values)
    const max = Math.max(...values)
    const width = (max - min) / bins || 1

    const nextBins: [string, number][] = Array.from({ length: bins }, (_, i) => {
      const lo = min + i * width
      const hi = lo + width
      const count = values.filter((v) => v >= lo && (i === bins - 1 ? v <= hi : v < hi)).length
      return [`${(lo * 100).toFixed(2)}%`, count]
    })

    const sorted = [...values].sort((a, b) => a - b)
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const median = sorted[Math.floor(sorted.length / 2)]

    return { binData: nextBins, meanVal: mean, medianVal: median }
  }, [values, bins])

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    if (binData.length === 0) {
      chart.setOption({
        animation: false,
        backgroundColor: 'transparent',
        series: [],
      })
    } else {
      const markLines: Array<{
        xAxis: string
        name: string
        lineStyle: { type: 'dashed'; color: string }
      }> = []

      if (markers.includes('mean')) {
        markLines.push({
          xAxis: `${(meanVal * 100).toFixed(2)}%`,
          name: 'Mean',
          lineStyle: { type: 'dashed', color: theme.amber },
        })
      }
      if (markers.includes('median')) {
        markLines.push({
          xAxis: `${(medianVal * 100).toFixed(2)}%`,
          name: 'Median',
          lineStyle: { type: 'dashed', color: theme.amber },
        })
      }

      chart.setOption({
        animation: true,
        backgroundColor: 'transparent',
        grid: { top: 16, right: 8, bottom: 40, left: 48 },
        xAxis: {
          type: 'category',
          data: binData.map(([label]) => label),
          axisLabel: {
            fontSize: 10,
            interval: Math.floor(bins / 5),
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
          },
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            fontSize: 10,
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
          },
          splitLine: { lineStyle: { color: theme.gridlineColor } },
        },
        series: [
          {
            type: 'bar',
            data: binData.map(([label, count]) => ({
              value: count,
              itemStyle: {
                color: parseFloat(label) < 0 ? `${theme.loss}66` : theme.secondaryText,
              },
            })),
            barMaxWidth: 8,
            markLine:
              markLines.length > 0
                ? { data: markLines, symbol: 'none', label: { show: false } }
                : undefined,
          },
        ],
        tooltip: {
          trigger: 'axis',
          backgroundColor: theme.tooltip.backgroundColor,
          borderColor: theme.tooltip.borderColor,
          textStyle: {
            color: theme.tooltip.textStyle.color,
            fontFamily: theme.monoFont,
            fontSize: 12,
          },
        },
      })
    }

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [binData, markers, meanVal, medianVal, theme, bins, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function ReturnHistogram({
  values,
  bins = 40,
  markers = ['mean', 'median'],
  title,
  height = 250,
  loading,
  error,
  syncGroup,
}: ReturnHistogramProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading} error={error} syncGroup={syncGroup}>
      <ReturnHistogramInner values={values} bins={bins} markers={markers} theme={theme} />
    </ChartFrame>
  )
}
