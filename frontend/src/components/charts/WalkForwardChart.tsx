/**
 * WalkForwardChart — grouped bar chart of IS vs OOS Sharpe per walk-forward fold.
 *
 * Architecture (F12 ChartFrame inner pattern):
 *   WalkForwardChart (outer) — renders ChartFrame, calls useChartTheme()
 *   ...Inner                 — accesses ChartFrameCtx, owns ECharts lifecycle
 *
 * Does NOT: fetch data, run validation, store filter state.
 */
import { useEffect, useRef } from 'react'
import { echarts } from '@/lib/echarts-setup'
import { ChartFrame, useChartFrame } from '@/components/charts/ChartFrame'
import { resolveCssVar, toRgba, useChartTheme, type EChartsTheme } from '@/lib/chart-theme'
import { dec } from '@/lib/fmt'

interface WalkForwardChartProps {
  folds: Array<{
    fold: number
    is_sharpe: number | null
    oos_sharpe: number | null
  }>
  loading?: boolean
}

interface InnerProps {
  folds: WalkForwardChartProps['folds']
  theme: EChartsTheme
}

function WalkForwardInner({ folds, theme }: InnerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const ctx = useChartFrame()

  useEffect(() => {
    if (!containerRef.current || !folds?.length) return

    void theme

    const amberColor = resolveCssVar('--amber-500', '#E8A33D')
    const infoColor = resolveCssVar('--info-500', '#4E9CDB')
    const lossColor = resolveCssVar('--loss-500', '#E05D5D')
    const textSecondary = resolveCssVar('--gray-400', '#7C8A9C')
    const borderColor = resolveCssVar('--gray-800', '#222A37')

    const categories = folds.map((f) => `Fold ${f.fold}`)

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
        trigger: 'axis',
        formatter: (
          params: Array<{ marker: string; seriesName: string; value: number | null }>,
        ) =>
          params
            .map(
              (p) =>
                `${p.marker}${p.seriesName}&nbsp;&nbsp;<b>${
                  p.value !== null ? dec(p.value, 2) : '—'
                }</b>`,
            )
            .join('<br>'),
      },
      series: [
        {
          name: 'IS Sharpe',
          type: 'bar',
          color: amberColor,
          barGap: '20%',
          data: folds.map((f) => ({
            value: f.is_sharpe ?? 0,
            itemStyle:
              f.is_sharpe !== null && f.is_sharpe < 0
                ? {
                    color: toRgba(lossColor, 0.12),
                    borderColor: lossColor,
                    borderWidth: 1,
                  }
                : {
                    color: toRgba(amberColor, 0.12),
                    borderColor: amberColor,
                    borderWidth: 1,
                  },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: textSecondary, type: 'dashed', width: 1 },
            data: [{ yAxis: 0 }],
          },
        },
        {
          name: 'OOS Sharpe',
          type: 'bar',
          color: infoColor,
          data: folds.map((f) => ({
            value: f.oos_sharpe ?? 0,
            itemStyle:
              f.oos_sharpe !== null && f.oos_sharpe < 0
                ? {
                    color: toRgba(lossColor, 0.12),
                    borderColor: lossColor,
                    borderWidth: 1,
                  }
                : {
                    color: toRgba(infoColor, 0.12),
                    borderColor: infoColor,
                    borderWidth: 1,
                  },
          })),
        },
      ],
    })

    const handleResize = () => chart.resize()
    globalThis.addEventListener('resize', handleResize)

    return () => {
      globalThis.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [folds, theme, ctx])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

export function WalkForwardChart({ folds, loading }: WalkForwardChartProps) {
  const theme = useChartTheme()
  return (
    <ChartFrame title="Walk-Forward Folds" height={280} loading={loading}>
      <WalkForwardInner folds={folds} theme={theme} />
    </ChartFrame>
  )
}
