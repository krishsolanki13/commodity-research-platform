import { useState } from 'react'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'
import { useFeatureCompute } from '@/api/hooks/useFeatureCompute'
import { PriceChart } from '@/components/charts/PriceChart'
import type { OverlayData } from '@/components/charts/PriceChart'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const EMPTY_OHLCV: ColumnarSeries = { index: [], columns: {} }

const PRESETS = [
  { key: 'ema_20', label: 'EMA 20', spec: { name: 'ema', params: { period: 20 } } },
  { key: 'ema_50', label: 'EMA 50', spec: { name: 'ema', params: { period: 50 } } },
  { key: 'sma_200', label: 'SMA 200', spec: { name: 'sma', params: { period: 200 } } },
] as const

type PresetKey = (typeof PRESETS)[number]['key']

interface AssetPricePanelProps {
  asset: string
  fromDate: string
  toDate: string
  displayName?: string
  ticker?: string
}

export function AssetPricePanel({
  asset,
  fromDate,
  toDate,
  displayName,
  ticker,
}: AssetPricePanelProps) {
  const [activePresets, setActivePresets] = useState<Set<PresetKey>>(new Set())

  const {
    data: ohlcv,
    isLoading,
    error,
  } = useAssetOhlcv(asset, {
    from_date: fromDate,
    to_date: toDate,
    downsample: 'view',
  })

  // One useFeatureCompute call per preset — always called (Rules of Hooks)
  // enabled: false when preset is not active (hook accepts null)
  const ema20 = useFeatureCompute(
    activePresets.has('ema_20')
      ? {
          asset,
          from_date: fromDate,
          to_date: toDate,
          specs: [{ name: 'ema', params: { period: 20 } }],
        }
      : null
  )
  const ema50 = useFeatureCompute(
    activePresets.has('ema_50')
      ? {
          asset,
          from_date: fromDate,
          to_date: toDate,
          specs: [{ name: 'ema', params: { period: 50 } }],
        }
      : null
  )
  const sma200 = useFeatureCompute(
    activePresets.has('sma_200')
      ? {
          asset,
          from_date: fromDate,
          to_date: toDate,
          specs: [{ name: 'sma', params: { period: 200 } }],
        }
      : null
  )

  const featureResults = { ema_20: ema20, ema_50: ema50, sma_200: sma200 }

  // OverlayData = { spec: FeatureSpecResponse, values: (number|null)[] }
  const overlays: OverlayData[] = PRESETS.filter((p) => activePresets.has(p.key)).flatMap((p) => {
    const result = featureResults[p.key]
    if (!result.data) return []
    const spec = result.data.specs[0]
    if (!spec) return []
    const values = result.data.columns.columns[spec.column_name] ?? []
    return [{ spec, values }]
  })

  function togglePreset(key: PresetKey) {
    setActivePresets((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const title = displayName && ticker ? `${displayName} · ${ticker}` : (displayName ?? asset)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            onClick={() => togglePreset(p.key)}
            aria-pressed={activePresets.has(p.key)}
            className={cn(
              'py-0.5 rounded border px-2 font-mono text-xs transition-colors',
              activePresets.has(p.key)
                ? 'border-accent text-accent'
                : 'border-border-strong text-text-secondary hover:text-text-primary'
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      <PriceChart
        ohlcv={ohlcv?.data ?? EMPTY_OHLCV}
        overlays={overlays}
        height="55vh"
        title={title}
        syncGroup="asset-detail"
        loading={isLoading}
        error={error}
      />
    </div>
  )
}
