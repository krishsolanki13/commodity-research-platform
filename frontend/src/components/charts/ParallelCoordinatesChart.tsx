// REQUIRES: ParallelChart + ParallelComponent registered in echarts-setup.ts
// Cursor adds these in TASK 1 of the cursor prompt — must be done before this renders

import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { dec } from '@/lib/fmt'
import type { components } from '@/api/schema'

type SweepRunSummaryResponse = components['schemas']['SweepRunSummaryResponse']

interface ParallelCoordinatesChartProps {
  runs: SweepRunSummaryResponse[]
  paramKeys: string[]
  loading?: boolean
}

interface InnerProps {
  runs: SweepRunSummaryResponse[]
  paramKeys: string[]
  theme: EChartsTheme
}

function ParallelCoordinatesInner({ runs, paramKeys, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !runs.length || !paramKeys.length) return

    const lossColor = resolveCssVar('--loss-500', '#E05D5D')
    const grayColor = resolveCssVar('--gray-500', '#5B6878')
    const gainColor = resolveCssVar('--gain-500', '#3FB68B')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')

    const sharpes = runs.map((r) => r.sharpe ?? 0)
    const minSharpe = Math.min(...sharpes)
    const maxSharpe = Math.max(...sharpes)

    // All axes: one per param + sharpe at the end (for visual map coloring)
    const sharpeAxisIndex = paramKeys.length

    const parallelAxis = [
      ...paramKeys.map((key, i) => ({
        dim: i,
        name: key,
        nameTextStyle: { color: textSecondary, fontSize: 11 },
        axisLabel: { color: textSecondary, fontSize: 10 },
      })),
      {
        dim: sharpeAxisIndex,
        name: 'Sharpe',
        nameTextStyle: { color: textSecondary, fontSize: 11 },
        axisLabel: {
          color: textSecondary,
          fontSize: 10,
          formatter: (v: number) => dec(v, 2),
        },
      },
    ]

    const seriesData = runs.map((run) => [
      ...paramKeys.map((k) => ((run.parameters as Record<string, unknown>)?.[k] as number) ?? 0),
      run.sharpe ?? 0,
    ])

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      parallelAxis,
      parallel: {
        left: 40,
        right: 40,
        top: 36,
        bottom: 48,
        lineStyle: { width: 1, opacity: 0.6 },
      },
      visualMap: {
        show: true,
        min: minSharpe,
        max: maxSharpe,
        dimension: sharpeAxisIndex,
        orient: 'horizontal',
        bottom: 4,
        left: 'center',
        itemWidth: 12,
        itemHeight: 80,
        text: ['High Sharpe', 'Low Sharpe'],
        textStyle: { color: textSecondary, fontSize: 10 },
        formatter: (v: number) => dec(v, 2),
        inRange: {
          color: [lossColor, grayColor, gainColor],
        },
      },
      series: [
        {
          type: 'parallel',
          lineStyle: { width: 1, opacity: 0.6 },
          data: seriesData,
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [runs, paramKeys, theme])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function ParallelCoordinatesChart({
  runs,
  paramKeys,
  loading,
}: ParallelCoordinatesChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Parameter Sensitivity" height={320} loading={loading}>
      <ParallelCoordinatesInner runs={runs} paramKeys={paramKeys} theme={theme} />
    </ChartFrame>
  )
}
