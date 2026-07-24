/**
 * AssetSharpeBarChart — horizontal bar chart of per-asset Sharpe ratios.
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   AssetSharpeBarChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                    — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Presentation only: consumes pre-computed asset_metrics from cached portfolio
 * data and reads the 'sharpe' key per asset.
 *
 * CRITICAL:
 *   - xAxis min: null — Sharpe CAN BE NEGATIVE; min: 0 would clip losing assets.
 *   - Bars colored by sign: gain fill/border for >= 0, loss fill/border for < 0.
 *   - Empty assetMetrics ({}) or all-null sharpe values → empty state, never throw.
 *
 * Does NOT: fetch data, compute metrics, store filter/zoom state.
 */
import { useEffect, useRef } from 'react'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { displayName } from '@/lib/commodity'
import type { ApiClientError } from '@/api/client'

// Matches PortfolioAssetsResponse.asset_metrics in the generated schema:
//   { [key: string]: { [key: string]: number | null } }
interface AssetSharpeBarChartProps {
  assetMetrics: Record<string, Record<string, number | null>>
  assets: string[]
  title?: string
  height?: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string }
}

// ---------------------------------------------------------------------------
// Inner component — owns ECharts lifecycle, accesses ChartFrameContext
// ---------------------------------------------------------------------------

interface AssetSharpeBarChartInnerProps {
  assetMetrics: Record<string, Record<string, number | null>>
  assets: string[]
  theme: EChartsTheme
}

function AssetSharpeBarChartInner({ assetMetrics, assets, theme }: AssetSharpeBarChartInnerProps) {
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
      grid: { left: 100, right: 60, top: '5%', bottom: '5%' },
      xAxis: {
        type: 'value' as const,
        min: null, // ← Sharpe CAN BE NEGATIVE — never clamp to 0
        axisLabel: {
          formatter: (v: number) => v.toFixed(2),
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
        formatter: (params: unknown) => {
          const p = (Array.isArray(params) ? params[0] : params) as {
            name?: string
            value?: number | { value?: number }
            marker?: string
          }
          const name = p?.name ?? ''
          const raw = typeof p?.value === 'object' && p?.value != null ? p.value.value : p?.value
          const value = Number(raw ?? 0)
          return `${name}<br/>${p?.marker ?? ''}Sharpe: ${value.toFixed(3)}`
        },
      },
      series: [
        {
          type: 'bar' as const,
          data: assets.map((a) => {
            const v = assetMetrics[a]?.['sharpe'] ?? null
            return {
              value: v ?? 0,
              itemStyle: {
                color: (v ?? 0) >= 0 ? theme.gainFill : theme.lossFill,
                borderColor: (v ?? 0) >= 0 ? theme.gain : theme.loss,
                borderWidth: 1,
              },
            }
          }),
          label: {
            show: true,
            position: 'right' as const,
            formatter: (p: unknown) => (p as { value: number }).value.toFixed(3),
            color: theme.secondaryText,
            fontFamily: theme.monoFont,
            fontSize: 10,
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              { xAxis: 0, lineStyle: { type: 'dashed' as const, color: theme.secondaryText } },
            ],
            label: { show: false },
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
  }, [assetMetrics, assets, theme, ctx])

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

// ---------------------------------------------------------------------------
// Outer component — renders ChartFrame, passes theme to inner
// ---------------------------------------------------------------------------

export function AssetSharpeBarChart({
  assetMetrics,
  assets,
  title = 'Per-Asset Sharpe Ratio',
  height = 240,
  loading,
  error,
  empty,
}: AssetSharpeBarChartProps) {
  const theme = useChartTheme()

  const allNull = assets.every((a) => (assetMetrics[a]?.['sharpe'] ?? null) === null)
  const isEmpty = assets.length === 0 || Object.keys(assetMetrics).length === 0 || allNull

  return (
    <ChartFrame
      title={title}
      height={height}
      loading={loading}
      error={error}
      empty={isEmpty ? (empty ?? { message: 'No per-asset Sharpe data available.' }) : undefined}
    >
      <AssetSharpeBarChartInner assetMetrics={assetMetrics} assets={assets} theme={theme} />
    </ChartFrame>
  )
}
