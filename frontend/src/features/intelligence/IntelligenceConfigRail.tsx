import { useMemo } from 'react'
import { z } from 'zod'
import { cn } from '@/lib/cn'
import { displayName } from '@/lib/commodity'
import { useUrlState } from '@/lib/useUrlState'
import { useAssets } from '@/api/hooks/useAssets'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

export const intelligenceSchema = z.object({
  asset: z.string().optional(),
  n_contracts: z.coerce.number().int().min(1).max(6).default(6),
  lookback: z.enum(['1Y', '3Y', '5Y', 'MAX']).default('3Y'),
  observation_date: z.string().optional(),
})

export type IntelligenceState = z.infer<typeof intelligenceSchema>

export const intelligenceDefaults: IntelligenceState = {
  n_contracts: 6,
  lookback: '3Y',
  observation_date: undefined,
}

const LOOKBACK_OPTIONS = ['1Y', '3Y', '5Y', 'MAX'] as const

export interface IntelligenceConfigRailProps {
  availableAssets: string[]
  loading?: boolean
}

export function IntelligenceConfigRail({ availableAssets, loading }: IntelligenceConfigRailProps) {
  const [urlState, setUrlState] = useUrlState(intelligenceSchema, intelligenceDefaults)

  const { data: assetsData } = useAssets()
  const assetMetaMap = useMemo(() => {
    const map = new Map<string, AssetMetadata>()
    assetsData?.assets?.forEach((a) => map.set(a.name, a))
    return map
  }, [assetsData])

  const assetOptions: AssetMetadata[] = availableAssets.map((name) => {
    const meta = assetMetaMap.get(name)
    return {
      name,
      display_name: meta?.display_name ?? displayName(name),
      ticker_continuous: meta?.ticker_continuous ?? '',
      contract_root: meta?.contract_root ?? '',
      exchange_suffix: meta?.exchange_suffix ?? '',
      exchange: meta?.exchange ?? '',
      currency: meta?.currency ?? 'USD',
      unit: meta?.unit ?? '',
      contract_multiplier: meta?.contract_multiplier ?? 1,
      tick_size: meta?.tick_size ?? 0.01,
      tick_value: meta?.tick_value ?? 1,
    }
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Asset
        </span>
        <AssetSelector
          value={urlState.asset ?? null}
          onChange={(v) => setUrlState({ asset: v ?? null })}
          assets={assetOptions}
          aria-label="Select commodity asset"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Contracts
        </span>
        <Select
          value={String(urlState.n_contracts)}
          onValueChange={(v) => setUrlState({ n_contracts: Number(v) })}
          disabled={loading}
        >
          <SelectTrigger className="w-full font-mono text-sm" aria-label="Number of contracts">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} contracts
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          History
        </span>
        <div className="inline-flex overflow-hidden rounded border border-border-strong">
          {LOOKBACK_OPTIONS.map((opt) => {
            const active = urlState.lookback === opt
            return (
              <button
                key={opt}
                type="button"
                aria-pressed={active}
                onClick={() => setUrlState({ lookback: opt })}
                className={cn(
                  'py-1.5 border-r border-border-strong px-3 font-mono text-xs',
                  'transition-colors last:border-r-0',
                  active
                    ? 'bg-bg-raised font-semibold text-text-emphasis'
                    : 'bg-bg-surface text-text-secondary hover:bg-bg-raised'
                )}
              >
                {opt}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
