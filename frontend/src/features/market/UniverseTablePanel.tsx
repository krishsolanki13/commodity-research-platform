import { useNavigate } from 'react-router-dom'
import { useAssets } from '@/api/hooks/useAssets'
import { useDataStatus } from '@/api/hooks/useDataStatus'
import { useUniverseOhlcv } from '@/api/hooks/useUniverseOhlcv'
import { UniverseGrid } from '@/components/data/UniverseGrid'
import { EmptyState } from '@/components/layout/EmptyState'
import { ErrorState } from '@/components/layout/ErrorState'
import { useUrlState } from '@/lib/useUrlState'
import { z } from 'zod'
import type { AssetRow } from '@/components/data/UniverseGrid'

const rangeSchema = z.object({
  range: z.enum(['1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX']).default('1Y'),
})

export function UniverseTablePanel() {
  const navigate = useNavigate()
  const { data: universe, isLoading, error } = useAssets()
  const { data: status } = useDataStatus()
  const [{ range }] = useUrlState(rangeSchema, { range: '1Y' })
  const ohlcvResults = useUniverseOhlcv(range)

  if (error) return <ErrorState error={error} />

  const rows: AssetRow[] = (universe?.assets ?? []).map((asset, idx) => {
    const summary = universe?.summaries[asset.name]
    const stat = status?.assets.find((a) => a.name === asset.name)
    const ohlcv = ohlcvResults[idx]?.data
    const closes = ohlcv?.data.columns.close ?? []
    const sparklineValues = closes.slice(-20)

    return {
      name: asset.name,
      displayName: asset.display_name,
      ticker: asset.ticker_continuous,
      exchange: asset.exchange,
      lastPrice: summary?.last_price ?? null,
      lastDate: summary?.last_date ?? null,
      return1d: summary?.return_1d ?? null,
      return1w: summary?.return_1w ?? null,
      return1m: summary?.return_1m ?? null,
      realizedVol63d: summary?.realized_vol_63d ?? null,
      avgVolume20d: summary?.avg_volume_20d ?? null,
      barCount: summary?.bar_count ?? 0,
      // Prefer summary so EmptyState test (assets-only mock) can force all-missing.
      dataHealth: summary?.data_health ?? stat?.data_health ?? 'missing',
      flaggedAnomalies: stat?.flagged_anomalies ?? summary?.flagged_anomalies ?? 0,
      sparklineValues,
    }
  })

  const allMissing = rows.length > 0 && rows.every((r) => r.dataHealth === 'missing')

  if (allMissing) {
    return (
      <EmptyState
        title="No market data yet"
        body="Ingest the universe to begin."
        action={{ label: 'Open Data Manager', href: '/system/data' }}
      />
    )
  }

  return (
    <UniverseGrid
      rows={rows}
      onRowClick={(name) => {
        void navigate(`/market/${name}`)
      }}
      loading={isLoading}
    />
  )
}
