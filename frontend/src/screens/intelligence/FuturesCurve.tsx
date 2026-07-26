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
import { Panel } from '@/ui/Panel'

export function FuturesCurve() {
  const [urlState] = useUrlState(intelligenceSchema, intelligenceDefaults)
  const { asset, n_contracts, lookback, observation_date } = urlState

  const { data: available, isLoading: availableLoading } = useCurveAvailableAssets()

  const {
    data: snapshot,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useCurveSnapshot(asset ?? '', n_contracts, observation_date)

  // History period (1Y/3Y/5Y/MAX) → lookback URL param → fromDate for HistoryPanel only.
  // KPI row uses useCurveSnapshot(observation_date) and is intentionally independent.
  const dateParams = rangeToDateParams(lookback ?? '3Y')

  return (
    <div className="flex gap-6 p-6">
      {/* Left sidebar — config card */}
      <div className="w-80 flex shrink-0 flex-col gap-4">
        <Panel title="Futures Curve">
          <div className="flex flex-col gap-4">
            <IntelligenceConfigRail
              availableAssets={available?.assets ?? []}
              loading={availableLoading}
            />
            <CurveDateControl />
          </div>
        </Panel>
      </div>

      {/* Right content */}
      <div className="flex flex-1 flex-col gap-6">
        {!asset && (
          <EmptyState
            title="Select an asset to view the futures curve"
            body="Choose a commodity from the selector to load term structure analytics."
          />
        )}

        {asset && (
          <>
            {asset && (
              <div className="flex items-center justify-between">
                <Link
                  to={`/intelligence/compare?assets=${asset}&n_contracts=${n_contracts}`}
                  className="font-mono text-xs text-text-accent hover:underline"
                >
                  Compare assets →
                </Link>
              </div>
            )}
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
              key={`${asset}-${dateParams.from_date}-${dateParams.to_date}-${n_contracts}`}
              asset={asset}
              fromDate={dateParams.from_date}
              toDate={dateParams.to_date}
              nContracts={n_contracts}
            />
            <ContractInventoryPanel snapshot={snapshot ?? null} loading={snapshotLoading} />
          </>
        )}
      </div>
    </div>
  )
}

export default FuturesCurve
