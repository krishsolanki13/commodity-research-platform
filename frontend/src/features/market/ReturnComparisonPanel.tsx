import { useEffect, useMemo, useRef } from 'react'
import { useUniverseOhlcv, ASSET_NAMES } from '@/api/hooks/useUniverseOhlcv'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import type { RangePreset } from '@/lib/date-range'

const DISPLAY_NAMES = ['Gold', 'Silver', 'Copper', 'WTI', 'Brent', 'Nat Gas']

function toIsoDate(epoch: number): string {
  return new Date(epoch).toISOString().slice(0, 10)
}

interface ReturnComparisonPanelProps {
  range: RangePreset
}

interface ReturnComparisonInnerProps {
  range: RangePreset
  theme: EChartsTheme
}

function ReturnComparisonInner({ range, theme }: ReturnComparisonInnerProps) {
  const results = useUniverseOhlcv(range)
  const divRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ECharts | null>(null)
  const ctx = useChartFrame()

  const { series, dates } = useMemo(() => {
    const dates: string[] = []
    const series = ASSET_NAMES.map((_, idx) => {
      const ohlcv = results[idx]?.data
      if (!ohlcv || ohlcv.data.columns.close.length === 0) {
        return { name: DISPLAY_NAMES[idx], data: [] as (number | null)[] }
      }
      const closes = ohlcv.data.columns.close
      const indexDates = ohlcv.data.index.map(toIsoDate)
      if (idx === 0) dates.push(...indexDates)

      const base = closes.find((v) => v !== null)
      if (base === null || base === undefined || base === 0) {
        return { name: DISPLAY_NAMES[idx], data: closes.map(() => null) }
      }

      const normalized = closes.map((v) =>
        v !== null ? parseFloat(((v / base - 1) * 100).toFixed(4)) : null
      )
      return { name: DISPLAY_NAMES[idx], data: normalized }
    })
    return { series, dates }
  }, [results])

  const isLoading = results.some((r) => r.isLoading)
  const isEmpty = series.every((s) => s.data.length === 0)

  useEffect(() => {
    if (!divRef.current || isLoading || isEmpty) return

    const chart = echarts.init(divRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    ctx?.onChartReady(chart)

    chart.setOption({
      animation: true,
      backgroundColor: 'transparent',
      grid: { top: 32, right: 16, bottom: 40, left: 56 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          fontSize: 10,
          rotate: 0,
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
          formatter: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
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
          const items = params as Array<{
            seriesName: string
            value: number | null
            color: string
            dataIndex: number
          }>
          const date = dates[items[0]?.dataIndex ?? 0] ?? ''
          const lines = items
            .filter((p) => p.value !== null && p.value !== undefined)
            .map(
              (p) =>
                `<span style="color:${p.color}">●</span> ${p.seriesName}: ${
                  p.value !== null ? `${p.value > 0 ? '+' : ''}${p.value.toFixed(2)}%` : '—'
                }`
            )
            .join('<br/>')
          return `${date}<br/>${lines}`
        },
      },
      legend: {
        top: 4,
        textStyle: {
          fontSize: 10,
          color: theme.secondaryText,
          fontFamily: theme.monoFont,
        },
      },
      series: series.map((s, idx) => ({
        name: s.name,
        type: 'line',
        data: s.data,
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 1.5 },
        color: theme.seriesPalette[idx] ?? theme.amber,
      })),
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [series, dates, theme, ctx, isLoading, isEmpty])

  if (isEmpty && !isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-text-secondary">
        No price data for this range.
      </div>
    )
  }

  return <div ref={divRef} style={{ width: '100%', height: '100%' }} />
}

export function ReturnComparisonPanel({ range }: ReturnComparisonPanelProps) {
  const theme = useChartTheme()
  const results = useUniverseOhlcv(range)
  const isLoading = results.some((r) => r.isLoading)

  return (
    <ChartFrame title="Returns" height={280} loading={isLoading}>
      <ReturnComparisonInner range={range} theme={theme} />
    </ChartFrame>
  )
}
