import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { fmtDate, dec } from '@/lib/fmt'

interface PCTimeSeriesChartProps {
  factorSeries: Record<string, (number | null)[]>
  indexEpochMs: number[]
  pcLabels: string[]
  loading?: boolean
}

interface InnerProps {
  factorSeries: Record<string, (number | null)[]>
  indexEpochMs: number[]
  pcLabels: string[]
  theme: EChartsTheme
}

const SERIES_COLORS = [
  { token: '--amber-500', fallback: '#E8A33D' },
  { token: '--info-500', fallback: '#4E9CDB' },
  { token: '--gain-500', fallback: '#3FB68B' },
]

function PCTimeSeriesInner({ factorSeries, indexEpochMs, pcLabels, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !indexEpochMs.length) return

    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')

    const categories = indexEpochMs.map((ms) => fmtDate(ms))

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      legend: {
        top: 4,
        right: 0,
        textStyle: { color: textSecondary, fontSize: 11 },
      },
      grid: { left: 12, right: 12, top: 36, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: textSecondary, fontSize: 11 },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { show: false },
        axisPointer: {
          label: {
            formatter: (p: { value: string | number }) => String(p.value),
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: textSecondary,
          fontSize: 11,
          formatter: (v: number) => dec(v, 1),
        },
        splitLine: { lineStyle: { color: borderColor } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: resolveCssVar('--gray-850', '#1A202B'),
        borderColor: resolveCssVar('--gray-700', '#2E3948'),
        borderWidth: 1,
        padding: [8, 12],
        textStyle: {
          color: resolveCssVar('--gray-200', '#C3CDD9'),
          fontSize: 12,
        },
        formatter: (
          params: Array<{
            marker: string
            seriesName: string
            value: number | null
            axisValue: string
          }>
        ) => {
          const header = `<div class="mb-1 font-mono text-xs">${params[0]?.axisValue ?? ''}</div>`
          const rows = params
            .map(
              (p) =>
                `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${
                  p.value !== null && p.value !== undefined ? dec(p.value, 3) : '—'
                }</b>`
            )
            .join('<br>')
          return header + rows
        },
      },
      series: pcLabels.map((label, i) => {
        const colorDef = SERIES_COLORS[i % SERIES_COLORS.length]
        const color = resolveCssVar(colorDef.token, colorDef.fallback)
        return {
          name: label,
          type: 'line',
          data: factorSeries[label] ?? [],
          connectNulls: false,
          lineStyle: { color, width: 1.5 },
          itemStyle: { color },
          symbol: 'none',
        }
      }),
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [factorSeries, indexEpochMs, pcLabels, theme])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function PCTimeSeriesChart({
  factorSeries,
  indexEpochMs,
  pcLabels,
  loading,
}: PCTimeSeriesChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="PC Factor Values Over Time" height={280} loading={loading}>
      <PCTimeSeriesInner
        factorSeries={factorSeries}
        indexEpochMs={indexEpochMs}
        pcLabels={pcLabels}
        theme={theme}
      />
    </ChartFrame>
  )
}
