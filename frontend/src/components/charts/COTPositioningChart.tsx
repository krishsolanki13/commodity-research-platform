import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { resolveCssVar, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { dec, fmtDate } from '@/lib/fmt'
import type { components } from '@/api/schema'

type COTDataResponse = components['schemas']['COTDataResponse']

function ordinalSuffix(n: number): string {
  const abs = Math.round(Math.abs(n))
  const mod100 = abs % 100
  const mod10 = abs % 10
  if (mod100 >= 11 && mod100 <= 13) return `${abs}th`
  if (mod10 === 1) return `${abs}st`
  if (mod10 === 2) return `${abs}nd`
  if (mod10 === 3) return `${abs}rd`
  return `${abs}th`
}

interface COTPositioningChartProps {
  records: COTDataResponse['records']
  loading?: boolean
}

interface InnerProps {
  records: COTDataResponse['records']
  theme: EChartsTheme
}

function COTPositioningInner({ records, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !records?.length) return

    const amberColor = resolveCssVar('--amber-500', '#E8A33D')
    const infoColor = resolveCssVar('--info-500', '#4E9CDB')
    const warnColor = resolveCssVar('--warn-500', '#D9A03C')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')
    const bgTooltip = resolveCssVar('--gray-850', '#1A202B')
    const borderTooltip = resolveCssVar('--gray-700', '#2E3948')
    const textPrimary = resolveCssVar('--gray-200', '#C3CDD9')

    const dates = records.map((r) => fmtDate(new Date(r.date).getTime()))
    const netSpec = records.map((r) => r.net_speculative ?? null)
    // percentile_rank is 0–100 from API; null/undefined → gap (not spike to 0)
    const pctRank = records.map((r) => {
      const v = r.percentile_rank
      return v === null || v === undefined ? null : v
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
      grid: { left: 12, right: 60, top: 36, bottom: '5%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: textSecondary, fontSize: 10 },
        axisLine: { lineStyle: { color: borderColor } },
        axisTick: { show: false },
        boundaryGap: false,
        axisPointer: {
          label: {
            formatter: (p: { value: string | number }) => String(p.value),
          },
        },
      },
      yAxis: [
        {
          type: 'value',
          axisLabel: { color: textSecondary, fontSize: 10 },
          splitLine: { lineStyle: { color: borderColor } },
          axisLine: { show: false },
          axisTick: { show: false },
        },
        {
          type: 'value',
          min: 0,
          max: 100,
          position: 'right',
          axisLabel: {
            color: textSecondary,
            fontSize: 10,
            formatter: (v: number) => `${v.toFixed(0)}%`,
          },
          splitLine: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
        },
      ],
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
            seriesName: string
            value: number | null
            axisValue: string
          }>
        ) => {
          const header = `<div class="mb-1 font-mono text-xs">${params[0]?.axisValue ?? ''}</div>`
          const rows = params
            .map((p) => {
              if (p.value === null || p.value === undefined) {
                return `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>—</b>`
              }
              const formatted =
                p.seriesName === 'Pct Rank'
                  ? `${ordinalSuffix(p.value)} percentile`
                  : dec(p.value, 0)
              return `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${formatted}</b>`
            })
            .join('<br>')
          return header + rows
        },
      },
      series: [
        {
          name: 'Net Speculative',
          type: 'line',
          yAxisIndex: 0,
          data: netSpec,
          lineStyle: { color: amberColor, width: 1.5 },
          itemStyle: { color: amberColor },
          symbol: 'none',
          connectNulls: false,
        },
        {
          name: 'Pct Rank',
          type: 'line',
          yAxisIndex: 1,
          data: pctRank,
          lineStyle: { color: infoColor, width: 1.5 },
          itemStyle: { color: infoColor },
          symbol: 'none',
          showAllSymbol: false,
          connectNulls: false,
          areaStyle: { color: infoColor, opacity: 0.08 },
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: warnColor, type: 'dashed', width: 1 },
            data: [{ yAxis: 80 }, { yAxis: 20 }],
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

export function COTPositioningChart({ records, loading }: COTPositioningChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="COT Net Speculative Positioning" height={280} loading={loading}>
      <COTPositioningInner records={records} theme={theme} />
    </ChartFrame>
  )
}
