import { useEIAData } from '@/api/hooks'
import { EIAInventoryChart } from '@/components/charts/EIAInventoryChart'

interface EIADataPanelProps {
  asset: string | null
}

export function EIADataPanel({ asset }: EIADataPanelProps) {
  const { data: eia, isLoading } = useEIAData(asset)

  if (!asset) return null

  if (isLoading) {
    return <div className="h-48 animate-pulse rounded border border-border-default bg-bg-raised" />
  }

  if (eia && !eia.available) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm font-medium text-text-primary">No EIA data available</p>
        <p className="mt-1 text-xs text-text-secondary">
          EIA weekly inventory reports cover US crude oil storage only.
          {asset !== 'wti' && asset !== 'brent'
            ? ' This asset is not tracked in EIA inventory data.'
            : ''}
        </p>
      </div>
    )
  }

  if (!eia?.records?.length) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm text-text-secondary">No EIA inventory records for this asset.</p>
      </div>
    )
  }

  return <EIAInventoryChart records={eia.records} />
}
