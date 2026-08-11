import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, toRgba, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { dec } from '@/lib/fmt'

interface PCLoadingsChartProps {
  loadings: Record<string, number[]>
  nContracts: number
  loading?: boolean
}

interface InnerProps {
  loadings: Record<string, number[]>
  nContracts: number
  theme: EChartsTheme
}

const SERIES_COLORS = [
  { token: '--amber-500', fallback: '#E8A33D' },
  { token: '--info-500', fallback: '#4E9CDB' },
  { token: '--gain-500', fallback: '#3FB68B' },
]

function PCLoadingsInner({ loadings, nContracts, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !loadings) return

    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')
    const pcKeys = Object.keys(loadings)
    const contractLabels = Array.from(
      { length: nContracts },
      (_, i) => `C${i + 1}`,
    )

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      legend: {
        top: 4,
        right: 0,
        textStyle: { color: textSecondary, fontSize: 11 },
      },
      grid: { left: 36, right: 20, top: 36, bottom: 28, containLabel: true },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: textSecondary,
          fontSize: 11,
          formatter: (v: number) => dec(v, 2),
        },
        splitLine: { lineStyle: { color: borderColor } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: contractLabels,
        axisLabel: { color: textSecondary, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        boundaryGap: true,
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
          params: Array<{ marker: string; seriesName: string; value: number }>,
        ) =>
          params
            .map(
              (p) =>
                `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${dec(p.value, 3)}</b>`,
            )
            .join('<br>'),
      },
      series: pcKeys.map((pc, i) => {
        const colorDef =
          SERIES_COLORS[i % SERIES_COLORS.length]
        const color = resolveCssVar(colorDef.token, colorDef.fallback)
        return {
          name: pc,
          type: 'bar',
          color,
          data: (loadings[pc] ?? []).map((v) => ({
            value: v,
            itemStyle: {
              color: toRgba(color, 0.35),
              borderColor: color,
              borderWidth: 1,
            },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: textSecondary, type: 'dashed', width: 1 },
            data: [{ xAxis: 0 }],
          },
        }
      }),
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [loadings, nContracts, theme])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function PCLoadingsChart({
  loadings,
  nContracts,
  loading,
}: PCLoadingsChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame
      title="PC Loadings by Contract Position"
      height={240}
      loading={loading}
    >
      <PCLoadingsInner
        loadings={loadings}
        nContracts={nContracts}
        theme={theme}
      />
    </ChartFrame>
  )
}
