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

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pt-6 pb-4">
        <h1 className="text-xl font-semibold text-text-primary">Data Manager</h1>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-3 gap-6 overflow-hidden px-6 pb-6">
        {/* Left — asset config (1/3) */}
        <div className="min-h-0 overflow-y-auto">
          <Panel title="Asset">
            <div className="flex flex-col gap-1.5">
              <AssetSelector
                value={selectedAsset}
                onChange={(v) => setUrlState({ asset: v ?? null })}
                assets={assetsData?.assets ?? []}
                aria-label="Select commodity asset"
              />
              <p className="mt-3 text-xs text-text-secondary">
                Select an asset to view data quality report, COT speculative
                positioning, and EIA inventory data.
              </p>
            </div>
          </Panel>
        </div>

        {/* Right — live data (2/3) */}
        <div className="col-span-2 min-h-0 overflow-y-auto">
          {!selectedAsset ? (
            <div className="rounded border border-border-default bg-bg-panel px-4 py-12 text-center">
              <p className="text-sm text-text-secondary">
                Select an asset to view QC report, COT positioning, and EIA
                inventory.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-8">
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
      </div>
    </div>
  )
}
