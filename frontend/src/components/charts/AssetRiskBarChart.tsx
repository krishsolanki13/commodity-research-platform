/**
 * AssetRiskBarChart — horizontal bar chart of per-asset VaR 99% (USD).
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   AssetRiskBarChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                  — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Presentation only: consumes a pre-computed per-asset VaR-99 map (USD loss
 * magnitudes) from cached portfolio data.
 *
 * CRITICAL:
 *   - xAxis min: 0 — VaR is a positive loss magnitude, never negative.
 *   - Bars always loss-colored (VaR is tail risk).
 *
 * Does NOT: fetch data, compute VaR, store filter/zoom state.
 */
import { useEffect, useRef } from 'react'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { displayName } from '@/lib/commodity'
import { fmt } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'

interface AssetRiskBarChartProps {
  assetVar99: Record<string, number>
  assets: string[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle, accesses ChartFrameContext
// ---------------------------------------------------------------------------

interface AssetRiskBarChartInnerProps {
  assetVar99: Record<string, number>
  assets: string[]
  theme: EChartsTheme
}

function AssetRiskBarChartInner({ assetVar99, assets, theme }: AssetRiskBarChartInnerProps) {
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!divRef.current) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { left: 110, right: 80, top: '5%', bottom: '5%' },
      xAxis: {
        type: 'value' as const,
        min: 0, // ← VaR is a positive loss magnitude, never negative
        axisLabel: {
          formatter: (v: number) => fmt.compactUsd(v),
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
          fontSize: 11,
        },
        splitLine: { lineStyle: { color: theme.gridlineColor } },
      },
      yAxis: {
        type: 'category' as const,
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
      },
      series: [
        {
          type: 'bar' as const,
          data: assets.map((a) => ({
            value: assetVar99[a] ?? 0,
            itemStyle: {
              color: theme.lossFill, // ← always loss-colored (VaR is tail risk)
              borderColor: theme.loss,
              borderWidth: 1,
            },
          })),
          label: {
            show: true,
            position: 'right' as const,
            formatter: (p: unknown) => fmt.compactUsd((p as { value: number }).value),
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
  }, [assetVar99, assets, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function AssetRiskBarChart({
  assetVar99,
  assets,
  title = 'Per-Asset VaR 99% (USD)',
  height = 240,
  loading,
  error,
}: AssetRiskBarChartProps) {
  const theme = useChartTheme()

  return (
    <ChartFrame title={title} height={height} loading={loading} error={error}>
      <AssetRiskBarChartInner assetVar99={assetVar99} assets={assets} theme={theme} />
    </ChartFrame>
  )
}
