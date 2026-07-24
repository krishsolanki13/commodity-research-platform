/**
 * ICDecayChart — IC at forward horizons {1, 2, 5, 10, 20 bars}.
 *
 * Categorical x-axis (not a time series) — no epoch handling needed.
 * Line + scatter overlay for per-point IC-band coloring.
 * Used by WorkbenchEvidenceCanvas (F5 Inc 4+); ICRollingChart is for F6.
 *
 * CRITICAL: connectNulls: false on the line series.
 *
 * Does NOT: compute IC decay, fetch data.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { components } from '@/api/schema'

type DecayEntry = components['schemas']['DecayEntry']

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ICDecayChartInnerProps {
  decay: DecayEntry[]
  theme: EChartsTheme
}

interface ICDecayChartProps {
  decay: DecayEntry[]
  title?: string
  height?: number | string
  loading?: boolean
}

const HORIZON_LABELS = ['1 bar', '2 bars', '5 bars', '10 bars', '20 bars']

// ---------------------------------------------------------------------------
// Inner component
// ---------------------------------------------------------------------------

function ICDecayChartInner({ decay, theme }: ICDecayChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const pointData = decay.map((d, i) => [i, d.ic] as [number, number | null])

    // Symmetric y-axis around 0 from non-null IC values
    const absValues = decay
      .map((d) => d.ic)
      .filter((v): v is number => v !== null)
      .map(Math.abs)
    const absMax = absValues.length > 0 ? Math.max(...absValues, 0.05) : 0.05

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 50, right: 48, top: '8%', bottom: '12%' },
      xAxis: {
        type: 'category' as const,
        data: HORIZON_LABELS,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitLine: { show: false },
      },
      yAxis: {
        min: -absMax,
        max: absMax,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (value: number) => value.toFixed(3),
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
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
          const items = (Array.isArray(params) ? params : [params]) as Array<{
            name?: string
            value?: number | [number, number | null]
            seriesType?: string
            marker?: string
          }>
          // Prefer the scatter/line point that carries [idx, ic]
          const point = items.find((p) => Array.isArray(p.value)) ?? items[0]
          const raw = Array.isArray(point?.value) ? point.value[1] : point?.value
          const label = point?.name ?? items[0]?.name ?? ''
          const marker = point?.marker ?? ''
          if (raw == null) return `${label}<br/>${marker}IC: —`
          return `${label}<br/>${marker}IC: ${Number(raw).toFixed(3)}`
        },
      },
      series: [
        {
          type: 'line' as const,
          data: pointData,
          connectNulls: false,
          lineStyle: { color: theme.amber, width: 1.5 },
          symbol: 'none',
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                yAxis: 0.05,
                lineStyle: { color: theme.icStrong, type: 'dashed' },
                label: {
                  formatter: '0.05',
                  position: 'end',
                  color: theme.secondaryText,
                  fontWeight: 'normal',
                  fontSize: 10,
                  fontFamily: theme.monoFont,
                },
              },
              {
                yAxis: 0.02,
                lineStyle: { color: theme.icWeak, type: 'dashed' },
                label: {
                  formatter: '0.02',
                  position: 'end',
                  color: theme.secondaryText,
                  fontWeight: 'normal',
                  fontSize: 10,
                  fontFamily: theme.monoFont,
                },
              },
              {
                yAxis: -0.02,
                lineStyle: { color: theme.icWeak, type: 'dashed' },
                label: {
                  formatter: '-0.02',
                  position: 'end',
                  color: theme.secondaryText,
                  fontWeight: 'normal',
                  fontSize: 10,
                  fontFamily: theme.monoFont,
                },
              },
              {
                yAxis: -0.05,
                lineStyle: { color: theme.icStrong, type: 'dashed' },
                label: {
                  formatter: '-0.05',
                  position: 'end',
                  color: theme.secondaryText,
                  fontWeight: 'normal',
                  fontSize: 10,
                  fontFamily: theme.monoFont,
                },
              },
              {
                yAxis: 0,
                lineStyle: { color: theme.secondaryText, type: 'solid' },
                label: { show: false },
              },
            ],
          },
        },
        {
          type: 'scatter' as const,
          data: pointData,
          symbolSize: 10,
          itemStyle: {
            // ECharts callback param typing is incomplete — cast from unknown per §17
            color: (params: unknown) => {
              const p = params as { value: [number, number | null] }
              const v = p.value[1]
              if (v === null || v === undefined) return theme.icNoise
              if (Math.abs(v) >= 0.05) return theme.icStrong
              if (Math.abs(v) >= 0.02) return theme.icWeak
              return theme.icNoise
            },
          },
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [decay, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component
// ---------------------------------------------------------------------------

export function ICDecayChart({ decay, title, height = 200, loading }: ICDecayChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading}>
      <ICDecayChartInner decay={decay} theme={theme} />
    </ChartFrame>
  )
}
