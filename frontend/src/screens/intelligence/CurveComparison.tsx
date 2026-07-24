import { Link } from 'react-router-dom'
import { useCurveSnapshots, type AssetSnapshotWithLabel } from '@/api/hooks'
import { CurveComparisonChart } from '@/components/charts/CurveComparisonChart'
import { RegimeComparisonTable } from '@/components/data/RegimeComparisonTable'
import { EmptyState } from '@/components/layout/EmptyState'
import { CompareConfigPanel, compareSchema } from '@/features/intelligence/CompareConfigPanel'
import { displayName } from '@/lib/commodity'
import { useUrlState } from '@/lib/useUrlState'
import { Panel } from '@/ui/Panel'

export function CurveComparison() {
  const [urlState] = useUrlState(compareSchema, { n_contracts: 4 })
  const assetList = (urlState.assets ?? '').split(',').filter(Boolean).slice(0, 4)
  const results = useCurveSnapshots(assetList, urlState.n_contracts)

  const assetSnapshots: AssetSnapshotWithLabel[] = results
    .map((result, index) => ({
      asset: assetList[index] ?? '',
      label: displayName(assetList[index] ?? ''),
      snapshot: result.data,
    }))
    .filter((snapshot): snapshot is AssetSnapshotWithLabel => snapshot.snapshot !== undefined)

  const loadingAny = results.some((result) => result.isLoading)

  return (
    <div className="flex h-full overflow-hidden">
      <CompareConfigPanel />
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-text-emphasis">Curve Comparison</h1>
          {assetList.length > 0 && (
            <Link
              to={`/intelligence?asset=${assetList[0]}`}
              className="font-mono text-xs text-text-accent hover:underline"
            >
              ← Single asset view
            </Link>
          )}
        </div>

        {assetList.length === 0 ? (
          <EmptyState
            title="Select assets to compare"
            body="Choose 2 to 4 commodities from the panel to overlay their forward curves."
          />
        ) : (
          <>
            <Panel title={`Normalized Forward Curves (${assetList.length} assets)`}>
              <CurveComparisonChart
                snapshots={assetSnapshots}
                height={350}
                loading={loadingAny && assetSnapshots.length === 0}
                empty={
                  assetSnapshots.length === 0 ? { message: 'No curve data loaded yet.' } : undefined
                }
              />
            </Panel>

            {assetSnapshots.length > 0 && (
              <Panel title="Regime Comparison">
                <RegimeComparisonTable snapshots={assetSnapshots} />
              </Panel>
            )}

            <p className="font-mono text-xs text-text-secondary">
              Curves normalized to front contract price. +1% = 1% premium over front.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
