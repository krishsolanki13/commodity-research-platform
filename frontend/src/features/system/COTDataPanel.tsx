import { useCOTData } from '@/api/hooks'
import { COTPositioningChart } from '@/components/charts/COTPositioningChart'
import type { components } from '@/api/schema'

type COTDataResponse = components['schemas']['COTDataResponse']

interface COTDataPanelProps {
  asset: string | null
}

export function COTDataPanel({ asset }: COTDataPanelProps) {
  const { data, isLoading } = useCOTData(asset)
  const cot = data as COTDataResponse | undefined

  if (!asset) return null

  if (isLoading) {
    return (
      <div className="h-64 animate-pulse rounded border border-border-default bg-bg-raised" />
    )
  }

  if (cot && !cot.available) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm font-medium text-text-primary">
          No COT data available
        </p>
        <p className="mt-1 text-xs text-text-secondary">{cot.message}</p>
      </div>
    )
  }

  if (!cot?.records?.length) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm text-text-secondary">
          No COT records for this asset.
        </p>
      </div>
    )
  }

  return <COTPositioningChart records={cot.records} />
}
