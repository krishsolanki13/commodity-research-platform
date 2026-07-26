import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { rangeToDateParams } from '@/lib/date-range'
import { useUrlState } from '@/lib/useUrlState'
import { useCurveAvailableAssets } from '@/api/hooks/useCurveAvailableAssets'
import { useCurveSnapshot } from '@/api/hooks/useCurveSnapshot'
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
import { Button } from '@/ui/button'

export function FuturesCurve() {
  const [urlState] = useUrlState(intelligenceSchema, intelligenceDefaults)
  const { asset, n_contracts, lookback, observation_date } = urlState

  const [launched, setLaunched] = useState(false)

  const { data: available, isLoading: availableLoading } = useCurveAvailableAssets()

  const {
    data: snapshot,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useCurveSnapshot(asset ?? '', n_contracts, observation_date)

  // History period (1Y/3Y/5Y/MAX) → lookback URL param → fromDate for HistoryPanel only.
  // KPI row uses useCurveSnapshot(observation_date) and is intentionally independent.
  const dateParams = rangeToDateParams(lookback ?? '3Y')

  // Reset launched view when asset changes so user always sees fresh config
  useEffect(() => {
    setLaunched(false)
  }, [asset])

  if (!launched) {
    return (
      <div className="flex flex-col gap-0 h-full overflow-hidden">
        {/* Title */}
        <div className="shrink-0 border-b border-border-default px-6 py-4">
          <h1 className="text-xl font-semibold text-text-primary">Futures Curve</h1>
        </div>

        <div className="flex min-h-0 flex-1 gap-6 overflow-hidden p-6">
          {/* Left panel */}
          <div className="w-96 shrink-0 overflow-y-auto">
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

          {/* Right half — View Curve button */}
          <div className="flex flex-1 flex-col gap-4 pt-0">
            <Button
              variant="primary"
              disabled={!asset}
              onClick={() => setLaunched(true)}
              className="w-full"
            >
              View Curve
            </Button>
            {!asset && (
              <p className="text-xs text-text-secondary">
                Select an asset to view the futures curve
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Futures Curve</h1>
        {asset && (
          <div className="flex items-center gap-4">
            <button
              onClick={() => setLaunched(false)}
              className="font-mono text-xs text-text-secondary hover:text-text-primary"
            >
              ← Change config
            </button>
            <Link
              to={`/intelligence/compare?assets=${asset}&n_contracts=${n_contracts}`}
              className="font-mono text-xs text-text-accent hover:underline"
            >
              Compare assets →
            </Link>
          </div>
        )}
      </div>

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
        asset={asset ?? ''}
        fromDate={dateParams.from_date}
        toDate={dateParams.to_date}
        nContracts={n_contracts}
      />
      <ContractInventoryPanel snapshot={snapshot ?? null} loading={snapshotLoading} />
    </div>
  )
}

export default FuturesCurve
