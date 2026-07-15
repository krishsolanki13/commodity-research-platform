import { useEffect, useMemo, useRef } from 'react'
import { useAssets } from '@/api/hooks/useAssets'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { ASSET_NAMES } from '@/api/hooks/useUniverseOhlcv'
import type { components } from '@/api/schema'

type UniverseResponse = components['schemas']['UniverseResponse']

const DISPLAY_NAMES = ['Gold', 'Silver', 'Copper', 'WTI', 'Brent', 'Nat Gas']

interface VolatilityInnerProps {
  universe: UniverseResponse | undefined
  theme: EChartsTheme
}

function VolatilityInner({ universe, theme }: VolatilityInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  const barValues = useMemo(
    () =>
      ASSET_NAMES.map((name) => {
        const v = universe?.summaries[name]?.realized_vol_63d ?? null
        return v !== null ? parseFloat((v * 100).toFixed(2)) : 0
      }),
    [universe]
  )

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { top: 16, right: 8, bottom: 40, left: 48 },
      xAxis: {
        type: 'category',
        data: DISPLAY_NAMES,
        axisLabel: {
          fontSize: 10,
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
          formatter: (v: number) => `${v.toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      series: [
        {
          type: 'bar',
          data: barValues,
          label: {
            show: true,
            position: 'top',
            fontSize: 10,
            color: theme.secondaryText,
            formatter: (params: { value: number }) => `${params.value.toFixed(1)}%`,
          },
          itemStyle: {
            color: theme.secondaryText,
          },
          barMaxWidth: 32,
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
        formatter: (params: unknown) => {
          const p = (params as Array<{ name: string; value: number }>)[0]
          return `${p.name}: ${p.value.toFixed(1)}%`
        },
      },
    })

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [barValues, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function VolatilityPanel() {
  const { data: universe, isLoading } = useAssets()
  const theme = useChartTheme()

  return (
    <ChartFrame title="Realized Vol (63d)" height={280} loading={isLoading}>
      <VolatilityInner universe={universe} theme={theme} />
    </ChartFrame>
  )
}
