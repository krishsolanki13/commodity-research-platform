import { useMemo } from 'react'
import { MetricGrid } from '@/components/data/MetricGrid'
import type { MetricStatProps } from '@/components/data/MetricStat'
import { fmt } from '@/lib/fmt'
import type { components } from '@/api/schema'

type AssetSummaryResponse = components['schemas']['AssetSummaryResponse']
type OhlcvResponse = components['schemas']['OhlcvResponse']

interface AssetMetricsPanelProps {
  asset: string
  summary: AssetSummaryResponse | null
  ohlcv?: OhlcvResponse | null
  loading?: boolean
}

export function AssetMetricsPanel({ asset, summary, ohlcv, loading }: AssetMetricsPanelProps) {
  const oneYearReturn = useMemo(() => {
    const closes = ohlcv?.data?.columns?.close?.filter((v): v is number => v !== null)
    if (!closes || closes.length < 252) return null
    const oneYearAgo = closes[closes.length - 252]
    const latest = closes[closes.length - 1]
    if (!oneYearAgo || !latest) return null
    return (latest - oneYearAgo) / oneYearAgo
  }, [ohlcv])

  // MetricStat accepts string | number. LAST uses fmt.price string directly so
  // trailing zeros are preserved (Number() would strip them).
  // When ohlcv yields a 1Y return, replace 1M% with 1Y% (6 metrics max, never 7).
  const periodReturnMetric: MetricStatProps =
    oneYearReturn !== null
      ? { label: '1Y%', value: oneYearReturn, format: 'percent' }
      : { label: '1M%', value: summary?.return_1m ?? null, format: 'percent' }

  const metrics: MetricStatProps[] = [
    {
      label: 'LAST',
      value: summary?.last_price != null ? fmt.price(summary.last_price, asset) : null,
      format: 'raw',
      tone: 'neutral',
      hint: summary?.last_date ?? undefined,
    },
    {
      label: '1D%',
      value: summary?.return_1d ?? null,
      format: 'percent',
    },
    {
      label: '1W%',
      value: summary?.return_1w ?? null,
      format: 'percent',
    },
    periodReturnMetric,
    {
      label: 'VOL 63D',
      value:
        summary !== null && (summary.bar_count ?? 0) >= 63
          ? (summary.realized_vol_63d ?? null)
          : null,
      format: 'percent',
      tone: 'neutral',
      hint:
        (summary?.bar_count ?? 0) < 63
          ? 'Insufficient bars (63 required)'
          : '63d realized volatility (annualized)',
    },
    {
      label: 'BARS',
      value: summary?.bar_count ?? null,
      format: 'integer',
      tone: 'neutral',
    },
  ]

  return <MetricGrid metrics={metrics} columns={6} loading={loading} />
}
