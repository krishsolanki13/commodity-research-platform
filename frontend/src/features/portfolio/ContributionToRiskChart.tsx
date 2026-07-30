/**
 * ContributionToRiskChart
 *
 * Horizontal bar chart showing each asset's share of portfolio strategy
 * volatility (asset_contribution_to_vol_pct from RiskReport).
 *
 * Values are strategy P&L vol contributions (NOT commodity price vol).
 * Bars sum to 100% by construction (CTR_pct = CTR_i / portfolio_vol).
 *
 * Follow the existing chart component pattern (e.g. CorrelationHeatmapChart):
 * if ChartFrame uses a children(theme, ref) render prop, wrap the inner div
 * and init call accordingly. The ECharts option below is engine-correct.
 */

import { useEffect, useRef } from "react"
import * as echarts from "echarts/core"
import { BarChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"
import type { TooltipComponentFormatterCallbackParams } from "echarts"
import { resolveCssVar } from "@/lib/chart-theme"

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

/** Format a 0–1 fraction as a percentage string (fmt.pct does not exist). */
function pct(value: number, digits: number): string {
  return `${(value * 100).toFixed(digits)}%`
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface ContributionToRiskChartProps {
  /** asset_contribution_to_vol_pct from RiskReport — values sum to ~1.0 */
  data: Record<string, number>
  height?: number
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ContributionToRiskChart({
  data,
  height = 140,
}: ContributionToRiskChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el || Object.keys(data).length === 0) return

    const chart = echarts.init(el)

    // Resolve tokens at render time — must not use CSS var() strings in ECharts
    const barColor     = resolveCssVar("--gain-500",       "#3FB68B")
    const textColor    = resolveCssVar("--text-secondary", "#7C8A9C")
    const gridColor    = resolveCssVar("--border-default", "#222A37")
    const bgPanel      = resolveCssVar("--bg-panel",       "#141922")
    const borderColor  = resolveCssVar("--border-default", "#222A37")
    const textPrimary  = resolveCssVar("--text-primary",   "#C3CDD9")

    // Sort ascending so longest bar is at top (ECharts category axis reads bottom-to-top)
    const entries = Object.entries(data).sort(([, a], [, b]) => a - b)
    const assetLabels = entries.map(([asset]) => asset.toUpperCase())
    const values      = entries.map(([, v]) => v)
    const maxVal      = Math.max(...values, 0.01)

    chart.setOption({
      grid: { left: 72, right: 60, top: 4, bottom: 4, containLabel: false },
      xAxis: {
        type: "value",
        max: maxVal * 1.15,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: gridColor, type: "dashed" } },
        axisLabel: {
          color: textColor,
          fontSize: 10,
          formatter: (v: number) => pct(v, 0),
        },
      },
      yAxis: {
        type: "category",
        data: assetLabels,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: textColor, fontSize: 11, fontFamily: "JetBrains Mono, monospace" },
      },
      series: [
        {
          type: "bar",
          data: values,
          barMaxWidth: 18,
          itemStyle: {
            color: barColor,
            borderRadius: [0, 3, 3, 0],
          },
          label: {
            show: true,
            position: "right",
            color: textColor,
            fontSize: 11,
            fontFamily: "JetBrains Mono, monospace",
            formatter: (p: { value: number }) => pct(p.value, 1),
          },
        },
      ],
      tooltip: {
        trigger: "axis",
        backgroundColor: bgPanel,
        borderColor: borderColor,
        borderWidth: 1,
        padding: [6, 10],
        textStyle: { color: textPrimary, fontSize: 12 },
        formatter: (params: TooltipComponentFormatterCallbackParams) => {
          if (!Array.isArray(params) || params.length === 0) return ""
          const p = params[0]
          const pctLabel = pct(Number(p.value), 2)
          return `${p.marker as string}${String(p.name)}: ${pctLabel} of strategy vol`
        },
      },
    })

    const onResize = () => chart.resize()
    window.addEventListener("resize", onResize)

    return () => {
      window.removeEventListener("resize", onResize)
      chart.dispose()
    }
  }, [data])

  return (
    <div
      ref={containerRef}
      style={{ height: `${height}px`, width: "100%" }}
      aria-label="Contribution to portfolio strategy volatility by asset"
    />
  )
}
