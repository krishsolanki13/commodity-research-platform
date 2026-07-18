import { Link } from 'react-router-dom'
import { rangeToDateParams } from '@/lib/date-range'
import { useUrlState } from '@/lib/useUrlState'
import { useCurveAvailableAssets } from '@/api/hooks/useCurveAvailableAssets'
import { useCurveSnapshot } from '@/api/hooks/useCurveSnapshot'
import { EmptyState } from '@/components/layout/EmptyState'
import {
  IntelligenceConfigRail,
  intelligenceSchema,
  intelligenceDefaults,
} from '@/features/intelligence/IntelligenceConfigRail'
import { CurveDateControl } from '@/features/intelligence/CurveDateControl'
import { CurveKPIRow } from '@/features/intelligence/CurveKPIRow'
import { CurvePanel } from '@/features/intelligence/CurvePanel'
import { BasisPanel } from '@/features/intelligence/BasisPanel'
import { HistoryPanel } from '@/features/intelligence/HistoryPanel'
import { ContractInventoryPanel } from '@/features/intelligence/ContractInventoryPanel'

export function FuturesCurve() {
  const [urlState] = useUrlState(intelligenceSchema, intelligenceDefaults)
  const { asset, n_contracts, lookback, observation_date } = urlState

  const { data: available, isLoading: availableLoading } = useCurveAvailableAssets()

  const {
    data: snapshot,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useCurveSnapshot(asset ?? '', n_contracts, observation_date)

  const dateParams = rangeToDateParams(lookback)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-emphasis">Futures Curve</h1>
        <div className="flex items-center gap-4">
          {asset && (
            <Link
              to={`/intelligence/compare?assets=${asset}&n_contracts=${n_contracts}`}
              className="font-mono text-xs text-text-accent hover:underline"
            >
              Compare assets →
            </Link>
          )}
          <span className="text-xs text-text-secondary">Commodity Intelligence · Phase 2</span>
        </div>
      </div>

      <IntelligenceConfigRail
        availableAssets={available?.assets ?? []}
        loading={availableLoading}
      />

      <CurveDateControl />

      {!asset && (
        <EmptyState
          title="Select an asset to view the futures curve"
          body="Choose a commodity from the selector to load term structure analytics."
        />
      )}

      {asset && (
        <>
          <CurveKPIRow snapshot={snapshot ?? null} loading={snapshotLoading} />

          <div className="grid grid-cols-2 gap-6">
            <CurvePanel
              snapshot={snapshot ?? null}
              loading={snapshotLoading}
              error={snapshotError instanceof Error ? snapshotError : null}
            />
            <BasisPanel snapshot={snapshot ?? null} loading={snapshotLoading} />
          </div>

          <HistoryPanel
            asset={asset}
            fromDate={dateParams.from_date}
            toDate={dateParams.to_date}
            nContracts={n_contracts}
          />

          <ContractInventoryPanel snapshot={snapshot ?? null} loading={snapshotLoading} />
        </>
      )}
    </div>
  )
}

export default FuturesCurve
