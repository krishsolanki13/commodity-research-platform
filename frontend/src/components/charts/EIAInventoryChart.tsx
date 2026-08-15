import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, toRgba, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { dec, fmtDate } from '@/lib/fmt'
import type { components } from '@/api/schema'

type EIADataResponse = components['schemas']['EIADataResponse']

interface EIAInventoryChartProps {
  records: EIADataResponse['records']
  loading?: boolean
}

interface InnerProps {
  records: EIADataResponse['records']
  theme: EChartsTheme
}

function EIAInventoryInner({ records, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !records?.length) return

    const gainColor = resolveCssVar('--gain-500', '#3FB68B')
    const lossColor = resolveCssVar('--loss-500', '#E05D5D')
    const warnColor = resolveCssVar('--warn-500', '#D9A03C')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')
    const bgTooltip = resolveCssVar('--gray-850', '#1A202B')
    const borderTooltip = resolveCssVar('--gray-700', '#2E3948')
    const textPrimary = resolveCssVar('--gray-200', '#C3CDD9')

    const dates = records.map((r) => fmtDate(new Date(r.date).getTime()))
    const zscores = records.map((r) => r.surprise_zscore ?? null)

    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    ctx?.onChartReady(chart)

    chart.setOption({
      backgroundColor: 'transparent',
      grid: { left: 12, right: 12, top: 16, bottom: '5%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          color: textSecondary,
          fontSize: 10,
          interval: Math.max(1, Math.floor(dates.length / 10)),
        },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { show: false },
        boundaryGap: true,
        axisPointer: {
          label: {
            formatter: (p: { value: string | number }) => String(p.value),
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: textSecondary,
          fontSize: 11,
          formatter: (v: number) => dec(v, 1),
        },
        splitLine: { lineStyle: { color: borderColor } },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: bgTooltip,
        borderColor: borderTooltip,
        borderWidth: 1,
        padding: [8, 12],
        textStyle: { color: textPrimary, fontSize: 12 },
        formatter: (
          params: Array<{
            marker: string
            name: string
            value: number | null
          }>
        ) => {
          const p = params[0]
          return `<div class="mb-1 font-mono text-xs">${p.name}</div>${p.marker}Inventory Surprise&nbsp;&nbsp;<b>${
            p.value !== null && p.value !== undefined ? `${dec(p.value, 2)}σ` : '—'
          }</b>`
        },
      },
      series: [
        {
          name: 'Inventory Surprise',
          type: 'bar',
          data: zscores.map((z) => ({
            value: z,
            itemStyle: {
              // Positive z = inventory build (bearish) = loss color
              // Negative z = inventory draw (bullish) = gain color
              color:
                z === null || z === undefined
                  ? borderColor
                  : z >= 0
                    ? toRgba(lossColor, 0.35)
                    : toRgba(gainColor, 0.35),
              borderColor:
                z === null || z === undefined ? borderColor : z >= 0 ? lossColor : gainColor,
              borderWidth: 1,
            },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: warnColor, type: 'dashed', width: 1 },
            data: [{ yAxis: 1 }, { yAxis: -1 }],
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
  }, [records, theme, ctx])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function EIAInventoryChart({ records, loading }: EIAInventoryChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="EIA Inventory Surprise (z-score)" height={240} loading={loading}>
      <EIAInventoryInner records={records} theme={theme} />
    </ChartFrame>
  )
}
