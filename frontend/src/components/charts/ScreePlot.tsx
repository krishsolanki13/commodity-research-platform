import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { pct } from '@/lib/fmt'

interface ScreePlotProps {
  evr: number[]
  cumEvr: number[]
  pcLabels: string[]
  loading?: boolean
}

interface InnerProps {
  evr: number[]
  cumEvr: number[]
  pcLabels: string[]
  theme: EChartsTheme
}

function ScreePlotInner({ evr, cumEvr, pcLabels, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !evr.length) return

    const amberColor = resolveCssVar('--amber-500', '#E8A33D')
    const infoColor = resolveCssVar('--info-500', '#4E9CDB')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      legend: {
        top: 4,
        right: 0,
        textStyle: { color: textSecondary, fontSize: 11 },
      },
      grid: { left: 12, right: 60, top: 36, bottom: 28, containLabel: true },
      xAxis: {
        type: 'category',
        data: pcLabels,
        axisLabel: { color: textSecondary, fontSize: 11 },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { show: false },
        boundaryGap: true,
      },
      yAxis: [
        {
          type: 'value',
          name: 'EVR',
          nameTextStyle: { color: textSecondary, fontSize: 10 },
          axisLabel: {
            color: textSecondary,
            fontSize: 11,
            formatter: (v: number) => pct(v, 0),
          },
          splitLine: { lineStyle: { color: borderColor } },
          axisLine: { show: false },
          axisTick: { show: false },
          min: 0,
          max: 1,
        },
        {
          type: 'value',
          name: 'Cumulative',
          nameTextStyle: { color: textSecondary, fontSize: 10 },
          axisLabel: {
            color: textSecondary,
            fontSize: 11,
            formatter: (v: number) => pct(v, 0),
          },
          splitLine: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          min: 0,
          max: 1,
          position: 'right',
        },
      ],
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
          params: Array<{ marker: string; seriesName: string; value: number }>,
        ) =>
          params
            .map(
              (p) => `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${pct(p.value, 1)}</b>`,
            )
            .join('<br>'),
      },
      series: [
        {
          name: 'Explained Variance',
          type: 'bar',
          yAxisIndex: 0,
          data: evr,
          itemStyle: { color: amberColor, borderRadius: [2, 2, 0, 0] },
          barMaxWidth: 48,
        },
        {
          name: 'Cumulative',
          type: 'line',
          yAxisIndex: 1,
          data: cumEvr,
          lineStyle: { color: infoColor, width: 2 },
          itemStyle: { color: infoColor },
          symbol: 'circle',
          symbolSize: 6,
          connectNulls: false,
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [evr, cumEvr, pcLabels, theme])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function ScreePlot({ evr, cumEvr, pcLabels, loading }: ScreePlotProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Explained Variance (Scree)" height={240} loading={loading}>
      <ScreePlotInner evr={evr} cumEvr={cumEvr} pcLabels={pcLabels} theme={theme} />
    </ChartFrame>
  )
}
