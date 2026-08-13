import { useEIAData } from '@/api/hooks'
import { EIAInventoryChart } from '@/components/charts/EIAInventoryChart'
import type { components } from '@/api/schema'

type EIADataResponse = components['schemas']['EIADataResponse']

interface EIADataPanelProps {
  asset: string | null
}

export function EIADataPanel({ asset }: EIADataPanelProps) {
  const { data, isLoading } = useEIAData(asset)
  const eia = data as EIADataResponse | undefined

  if (!asset) return null

  if (isLoading) {
    return (
      <div className="h-48 animate-pulse rounded border border-border-default bg-bg-raised" />
    )
  }

  if (eia && !eia.available) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm font-medium text-text-primary">
          No EIA data available
        </p>
        <p className="mt-1 text-xs text-text-secondary">{eia.message}</p>
      </div>
    )
  }

  if (!eia?.records?.length) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm text-text-secondary">
          No EIA inventory records for this asset.
        </p>
      </div>
    )
  }

  return <EIAInventoryChart records={eia.records} />
}
