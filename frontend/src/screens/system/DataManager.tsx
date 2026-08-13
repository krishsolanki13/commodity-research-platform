import { z } from 'zod'
import { useUrlState } from '@/lib/useUrlState'
import { useAssets } from '@/api/hooks'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { DataQCPanel } from '@/features/system/DataQCPanel'
import { COTDataPanel } from '@/features/system/COTDataPanel'
import { EIADataPanel } from '@/features/system/EIADataPanel'

const dataManagerSchema = z.object({
  asset: z.string().optional(),
})

const dataManagerDefaults = {
  asset: undefined as string | undefined,
}

export default function DataManagerScreen() {
  const [urlState, setUrlState] = useUrlState(dataManagerSchema, dataManagerDefaults)
  const selectedAsset = urlState.asset ?? null
  const { data: assetsData } = useAssets()

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="shrink-0 px-6 pt-6 pb-4">
        <h1 className="text-xl font-semibold text-text-primary">Data Manager</h1>
      </div>

      <div className="flex flex-col gap-8 px-6 pb-6">
        <section>
          <div className="mb-3">
            <span className="font-mono text-sm">Asset</span>
          </div>
          <div className="max-w-sm">
            <AssetSelector
              value={selectedAsset}
              onChange={(v) => setUrlState({ asset: v ?? null })}
              assets={assetsData?.assets ?? []}
              aria-label="Select commodity asset"
            />
          </div>
          {!selectedAsset && (
            <p className="mt-2 text-xs text-text-secondary">
              Select an asset to view QC report, COT positioning, and EIA inventory.
            </p>
          )}
        </section>

        {/* QC Report */}
        <section>
          <div className="mb-3">
            <span className="font-mono text-sm">QC Report</span>
          </div>
          <DataQCPanel asset={selectedAsset} />
        </section>

        {/* COT Positioning */}
        <section>
          <div className="mb-3">
            <span className="font-mono text-sm">COT Positioning</span>
          </div>
          <COTDataPanel asset={selectedAsset} />
        </section>

        {/* EIA Inventory */}
        <section>
          <div className="mb-3">
            <span className="font-mono text-sm">EIA Inventory</span>
          </div>
          <EIADataPanel asset={selectedAsset} />
        </section>
      </div>
    </div>
  )
}
