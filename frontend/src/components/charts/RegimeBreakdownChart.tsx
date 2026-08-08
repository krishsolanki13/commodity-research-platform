/**
 * RegimeBreakdownChart — grouped bars of Sharpe / Total Return % by term-structure regime.
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   RegimeBreakdownChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                     — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * F18 colors: contango=amber/warn, backwardation=gain, flat=gray.
 * Does NOT: fetch data, compute attribution, store filter state.
 */
import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { resolveCssVar, toRgba, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { dec, pct } from '@/lib/fmt'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

interface RegimeBreakdownChartProps {
  data: RegimeAttributionResponse
  loading?: boolean
}

interface InnerProps {
  data: RegimeAttributionResponse
  theme: EChartsTheme
}

// F18-confirmed: contango=amber/warn, backwardation=gain/green, flat=gray
const REGIME_DISPLAY: Record<string, string> = {
  contango: 'Contango',
  backwardation: 'Backwardation',
  flat: 'Flat',
}

const REGIME_TOKEN: Record<string, string> = {
  contango: '--warn-500',
  backwardation: '--gain-500',
  flat: '--gray-500',
}

const REGIME_FALLBACK: Record<string, string> = {
  contango: '#D9A03C',
  backwardation: '#3FB68B',
  flat: '#5B6878',
}

function RegimeBreakdownInner({ data, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !data?.regime_metrics) return

    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')

    const regimes = ['contango', 'backwardation', 'flat'].filter(
      (r) => data.regime_metrics[r] !== undefined,
    )
    const categories = regimes.map((r) => REGIME_DISPLAY[r] ?? r)

    const sharpeData = regimes.map((r) => {
      const color = resolveCssVar(REGIME_TOKEN[r], REGIME_FALLBACK[r])
      return {
        value: data.regime_metrics[r]?.sharpe ?? 0,
        itemStyle: {
          color: toRgba(color, 0.35),
          borderColor: color,
          borderWidth: 1,
        },
      }
    })

    const returnData = regimes.map((r) => {
      const color = resolveCssVar(REGIME_TOKEN[r], REGIME_FALLBACK[r])
      return {
        value: (data.regime_metrics[r]?.total_return ?? 0) * 100,
        itemStyle: {
          color: toRgba(color, 0.18),
          borderColor: color,
          borderWidth: 1,
          borderType: 'dashed' as const,
        },
      }
    })

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
        boundaryGap: true,
      },
      yAxis: {
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
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
        backgroundColor: theme.tooltip.backgroundColor,
        borderColor: theme.tooltip.borderColor,
        textStyle: {
          color: theme.tooltip.textStyle.color,
          fontFamily: theme.monoFont,
          fontSize: 12,
        },
        formatter: (
          params: Array<{
            marker: string
            seriesName: string
            value: number
            name: string
          }>,
        ) => {
          const heading = params[0]?.name ?? ''
          const rows = params
            .map((p) => {
              const formatted =
                p.seriesName === 'Total Return %'
                  ? pct(p.value / 100, 1)
                  : dec(p.value, 2)
              return `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${formatted}</b>`
            })
            .join('<br>')
          return `${heading}<br>${rows}`
        },
      },
      series: [
        {
          name: 'Sharpe',
          type: 'bar',
          barGap: '20%',
          data: sharpeData,
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: textSecondary, type: 'dashed', width: 1 },
            data: [{ yAxis: 0 }],
          },
        },
        {
          name: 'Total Return %',
          type: 'bar',
          data: returnData,
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [data, theme, ctx])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function RegimeBreakdownChart({ data, loading }: RegimeBreakdownChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Performance by Term Structure Regime" height={280} loading={loading}>
      <RegimeBreakdownInner data={data} theme={theme} />
    </ChartFrame>
  )
}
