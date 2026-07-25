import { useParams, useSearchParams, Navigate, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAssets } from '@/api/hooks/useAssets'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'
import { useAssetSummary } from '@/api/hooks/useAssetSummary'
import { useDataStatus } from '@/api/hooks/useDataStatus'
import { useCurveAvailableAssets } from '@/api/hooks/useCurveAvailableAssets'
import { AssetHeader } from '@/features/market/AssetHeader'
import { AssetMetricsPanel } from '@/features/market/AssetMetricsPanel'
import { AssetPricePanel } from '@/features/market/AssetPricePanel'
import { AssetDistributionPanel } from '@/features/market/AssetDistributionPanel'
import { AssetMetadataPanel } from '@/features/market/AssetMetadataPanel'
import { AssetRunsPanel } from '@/features/market/AssetRunsPanel'
import { ValidationRibbon } from '@/components/layout/ValidationRibbon'
import { ErrorState } from '@/components/layout/ErrorState'

export default function AssetDetailScreen() {
  const { asset } = useParams<{ asset: string }>()
  const [, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // Full history date range — declared before hooks that use it (Rules of Hooks)
  const fromDate = '2010-01-01'
  const toDate = new Date().toISOString().slice(0, 10)

  const { data: universe } = useAssets()
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useAssetSummary(asset ?? '')
  const { data: status } = useDataStatus(asset ?? undefined)
  const {
    data: ohlcv,
    isLoading: ohlcvLoading,
    error: ohlcvError,
  } = useAssetOhlcv(asset ?? '', {
    from_date: fromDate,
    to_date: toDate,
    downsample: 'view',
  })
  const { data: curveAvailable } = useCurveAvailableAssets()
  const hasContractData = curveAvailable?.assets.includes(asset ?? '') ?? false

  // Sync asset to URL search params for ContextBar chip
  useEffect(() => {
    if (!asset) return
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('asset', asset)
        return next
      },
      { replace: true }
    )
  }, [asset, setSearchParams])

  if (!asset) return <Navigate to="/market" replace />

  // Unknown asset — summary returns 404
  if (summaryError) {
    return (
      <div className="p-6">
        <ErrorState error={summaryError} />
      </div>
    )
  }

  const metadata = universe?.assets.find((a) => a.name === asset) ?? null
  const assetStatus = status?.assets.find((a) => a.name === asset)
  const flags = assetStatus?.flags ?? []
  const hasFlags = flags.length > 0

  return (
    <div className="flex flex-col gap-6 p-6">
      <AssetHeader asset={asset} metadata={metadata} hasContractData={hasContractData} />
      <AssetMetricsPanel
        asset={asset}
        summary={summary ?? null}
        ohlcv={ohlcv ?? null}
        loading={summaryLoading}
      />
      {hasFlags && (
        <ValidationRibbon
          flags={flags}
          onView={() => {
            void navigate(`/system/data?asset=${asset}`)
          }}
        />
      )}
      <AssetPricePanel
        asset={asset}
        fromDate={fromDate}
        toDate={toDate}
        displayName={metadata?.display_name}
        ticker={metadata?.ticker_continuous}
        ohlcv={ohlcv ?? null}
        loading={ohlcvLoading}
        error={ohlcvError}
      />
      <div className="grid grid-cols-2 gap-6">
        <AssetDistributionPanel asset={asset} fromDate={fromDate} toDate={toDate} />
        <AssetMetadataPanel metadata={metadata} />
      </div>
      <AssetRunsPanel asset={asset} displayName={metadata?.display_name ?? asset} />
    </div>
  )
}
