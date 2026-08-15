/**
 * ICRollingChart — rolling information coefficient as band-colored bars.
 *
 * Built in F5 for use in F6 Run Detail Signal Quality tab.
 * NOT used in WorkbenchEvidenceCanvas (which uses ICDecayChart instead).
 *
 * Per-bar color thresholds: |IC| >= 0.05 → icStrong, >= 0.02 → icWeak, else icNoise.
 * Five threshold markLines: ±0.05, ±0.02, and zero.
 *
 * Does NOT: compute IC, fetch data.
 */
import { useEffect, useRef } from 'react'
import type { ECharts } from '@/lib/echarts-setup'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { dec, fmtDate } from '@/lib/fmt'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ICRollingChartInnerProps {
  ic: ColumnarSeries
  window: number
  theme: EChartsTheme
}

interface ICRollingChartProps {
  ic: ColumnarSeries
  window: number
  title?: string
  height?: number | string
  loading?: boolean
}

// ---------------------------------------------------------------------------
// Inner component
// ---------------------------------------------------------------------------

function ICRollingChartInner({ ic, window: _window, theme }: ICRollingChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    const cols = ic.columns as Record<string, (number | null)[]>
    const values = cols['value'] ?? []

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 50, right: 48, top: '8%', bottom: '12%' },
      xAxis: {
        type: 'category' as const,
        data: ic.index,
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
          formatter: (v: string | number) => fmtDate(Number(v)),
        },
        axisPointer: {
          label: {
            formatter: (p: { value: string | number }) => fmtDate(Number(p.value)),
          },
        },
        splitLine: { show: false },
      },
      yAxis: {
        // symmetric auto-scale — let ECharts compute min/max from data
        axisLabel: {
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
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
            axisValue?: string | number
            name?: string | number
            value?: number | null
            marker?: string
          }>
          const p = items[0]
          if (!p) return ''
          const header = fmtDate(Number(p.axisValue ?? p.name))
          const marker = p.marker ?? ''
          if (p.value == null) return `${header}<br/>${marker}IC: —`
          return `${header}<br/>${marker}IC: ${dec(Number(p.value), 3)}`
        },
      },
      series: [
        {
          type: 'bar' as const,
          data: values,
          itemStyle: {
            // ECharts callback param typing is incomplete — cast from unknown per §17
            color: (params: unknown) => {
              const p = params as { value: [number, number] | number }
              const v = Array.isArray(p.value) ? p.value[1] : p.value
              if (Math.abs(v) >= 0.05) return theme.icStrong
              if (Math.abs(v) >= 0.02) return theme.icWeak
              return theme.icNoise
            },
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                yAxis: 0.05,
                lineStyle: { color: theme.icStrong, type: 'dashed' },
                label: {
                  formatter: '+0.05',
                  position: 'end',
                  offset: [4, -8],
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
                  formatter: '+0.02',
                  position: 'end',
                  offset: [4, 8],
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
                  offset: [4, -8],
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
                  offset: [4, 8],
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
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [ic, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component
// ---------------------------------------------------------------------------

export function ICRollingChart({ ic, window, title, height = 200, loading }: ICRollingChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading}>
      <ICRollingChartInner ic={ic} window={window} theme={theme} />
    </ChartFrame>
  )
}
