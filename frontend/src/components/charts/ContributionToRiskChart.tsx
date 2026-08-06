/**
 * ContributionToRiskChart — horizontal bar chart of each asset's % contribution
 * to portfolio volatility (asset_contribution_to_vol_pct).
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   ContributionToRiskChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                        — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Bars use --info-500 (not gain/loss) — contribution is compositional, not P&L.
 *
 * Does NOT: fetch data, compute contributions, store filter/zoom state.
 */
import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { resolveCssVar, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { displayName } from '@/lib/commodity'
import { pct } from '@/lib/fmt'

interface ContributionToRiskChartProps {
  data: Record<string, number> // asset_contribution_to_vol_pct — fractions summing ~1.0
  loading?: boolean
}

interface InnerProps {
  data: Record<string, number>
  theme: EChartsTheme
}

function ContributionToRiskInner({ data, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !data) return

    void theme // re-derive CSS vars when workspace theme toggles

    const assets = Object.keys(data)
    const values = assets.map((a) => data[a])

    const infoColor = resolveCssVar('--info-500', '#4E9CDB')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderDefault = resolveCssVar('--gray-800', '#222A37')

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      grid: { left: 110, right: 80, top: '5%', bottom: '5%' },
      xAxis: {
        type: 'value',
        axisLabel: {
          color: textSecondary,
          fontSize: 11,
          formatter: (v: number) => pct(v, 1),
        },
        splitLine: { lineStyle: { color: borderDefault } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'category',
        data: assets.map((a) => displayName(a)),
        axisLabel: { color: textSecondary, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: 'bar',
          data: values,
          itemStyle: { color: infoColor, borderRadius: [0, 2, 2, 0] },
          label: {
            show: true,
            position: 'right',
            formatter: (p: { value: number }) => pct(p.value, 1),
            color: textSecondary,
            fontSize: 10,
          },
        },
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: Array<{ marker: string; name: string; value: number }>) => {
          const p = params[0]
          return `${p.marker}${p.name}&nbsp;&nbsp;<b>${pct(p.value, 1)}</b>`
        },
      },
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

export function ContributionToRiskChart({ data, loading }: ContributionToRiskChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Vol Contribution by Asset" height={200} loading={loading}>
      <ContributionToRiskInner data={data} theme={theme} />
    </ChartFrame>
  )
}
