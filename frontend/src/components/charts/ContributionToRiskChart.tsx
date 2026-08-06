/**
 * ContributionToRiskChart — horizontal bar chart of each asset's % contribution
 * to portfolio volatility (asset_contribution_to_vol_pct).
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   ContributionToRiskChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                        — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Visual template matches AssetRiskBarChart (semi-transparent fill + solid border,
 * grid, fonts, tooltip). Hue is info-500 — contribution is compositional, not P&L.
 *
 * Does NOT: fetch data, compute contributions, store filter/zoom state.
 */
import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { resolveCssVar, toRgba, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
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
  const divRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const assets = Object.keys(data)
    const infoColor = resolveCssVar('--info-500', '#4E9CDB')

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 110, right: 80, top: '5%', bottom: '5%' },
      xAxis: {
        type: 'value' as const,
        min: 0,
        axisLabel: {
          formatter: (v: number) => pct(v, 1),
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      yAxis: {
        type: 'category' as const,
        // Explicit: AssetRiskBarChart relies on ECharts category default (true).
        // Set explicitly so axis overhang past first/last category is guaranteed.
        boundaryGap: true,
        data: assets.map((a) => displayName(a)),
        axisLabel: { color: theme.secondaryText, fontFamily: theme.monoFont, fontSize: 11 },
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
        formatter: (params: unknown) => {
          const p = (Array.isArray(params) ? params[0] : params) as {
            name?: string
            value?: number | { value?: number }
            marker?: string
          }
          const name = p?.name ?? ''
          const raw = typeof p?.value === 'object' && p?.value != null ? p.value.value : p?.value
          const value = Number(raw ?? 0)
          return `${name}<br/>${p?.marker ?? ''}Vol Contribution: ${pct(value, 1)}`
        },
      },
      series: [
        {
          type: 'bar' as const,
          data: assets.map((a) => ({
            value: data[a] ?? 0,
            itemStyle: {
              // Match AssetRiskBarChart: --loss-900a alpha is 0.12 + borderWidth 1
              color: toRgba(infoColor, 0.12),
              borderColor: infoColor,
              borderWidth: 1,
            },
          })),
          label: {
            show: true,
            position: 'right' as const,
            formatter: (p: unknown) => pct((p as { value: number }).value, 1),
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 10,
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
  }, [data, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function ContributionToRiskChart({ data, loading }: ContributionToRiskChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Vol Contribution by Asset" height={220} loading={loading}>
      <ContributionToRiskInner data={data} theme={theme} />
    </ChartFrame>
  )
}
