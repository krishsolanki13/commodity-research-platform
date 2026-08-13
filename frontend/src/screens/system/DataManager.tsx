import { z } from 'zod'
import { useUrlState } from '@/lib/useUrlState'
import { useAssets } from '@/api/hooks'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { DataQCPanel } from '@/features/system/DataQCPanel'
import { COTDataPanel } from '@/features/system/COTDataPanel'
import { EIADataPanel } from '@/features/system/EIADataPanel'
import { Panel } from '@/ui/Panel'

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

  function handleChangeAsset() {
    setUrlState({ asset: null })
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pb-4 pt-6">
        <h1 className="text-xl font-semibold text-text-primary">Data Manager</h1>
      </div>

      {!selectedAsset ? (
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
          <div className="min-h-0 overflow-y-auto">
            <Panel title="Asset">
              <div className="gap-1.5 flex flex-col">
                <AssetSelector
                  value={selectedAsset}
                  onChange={(v) => setUrlState({ asset: v ?? null })}
                  assets={assetsData?.assets ?? []}
                  aria-label="Select commodity asset"
                />
                <p className="mt-3 text-xs text-text-secondary">
                  Select an asset to view data quality, COT positioning, and EIA inventory data.
                </p>
              </div>
            </Panel>
          </div>

          <div className="min-h-0 overflow-y-auto">
            <Panel title="View">
              <p className="text-xs text-text-secondary">
                Select an asset to view QC report, COT positioning, and EIA inventory.
              </p>
            </Panel>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-6 pb-6">
          <button
            type="button"
            onClick={handleChangeAsset}
            className="gap-1.5 flex w-fit items-center text-sm text-text-secondary transition-colors hover:text-text-primary"
          >
            ← Change Asset
          </button>

          <section>
            <div className="mb-3">
              <span className="font-mono text-sm">QC Report</span>
            </div>
            <DataQCPanel asset={selectedAsset} />
          </section>

          <section>
            <div className="mb-3">
              <span className="font-mono text-sm">COT Positioning</span>
            </div>
            <COTDataPanel asset={selectedAsset} />
          </section>

          <section>
            <div className="mb-3">
              <span className="font-mono text-sm">EIA Inventory</span>
            </div>
            <EIADataPanel asset={selectedAsset} />
          </section>
        </div>
      )}
    </div>
  )
}
