/**
 * PortfolioRegimePanel — per-asset regime attribution for a portfolio run.
 *
 * Opt-in compute via shouldFetch — does not auto-fetch on mount (avoids
 * blocking the single-worker API).
 */
import { useMemo, useRef, useState } from 'react'
import { Info } from 'lucide-react'
import {
  useRegimeAttributionCompute,
  useRegimeAttributionJobStatus,
  useRegimeAttributionJobResult,
} from '@/api/hooks'
import { RegimeBreakdownChart } from '@/components/charts/RegimeBreakdownChart'
import { displayName } from '@/lib/commodity'
import { pct } from '@/lib/fmt'
import { Button } from '@/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'

interface PortfolioRegimePanelProps {
  runId: string
  assetRunIds: Record<string, string | null> | null | undefined
}

// F18-confirmed regime text colors — no background fills
const REGIME_TEXT_CLASS: Record<string, string> = {
  contango: 'text-warn',
  backwardation: 'text-gain',
  flat: 'text-text-secondary',
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1)
}

export function PortfolioRegimePanel({ runId: _runId, assetRunIds }: PortfolioRegimePanelProps) {
  const availableAssets = useMemo(
    () =>
      Object.entries(assetRunIds ?? {})
        .filter(([, id]) => id !== null)
        .map(([asset]) => asset)
        .sort(),
    [assetRunIds]
  )

  // Selected asset state — default to first alphabetically
  const defaultAsset = availableAssets[0] ?? ''
  const [selectedAsset, setSelectedAsset] = useState<string>('')
  const effectiveAsset = selectedAsset || defaultAsset

  // Map of asset → jobId, persists across asset switches
  const jobIdByAsset = useRef<Record<string, string>>({})

  // Derived from the map for the current asset
  const jobId = effectiveAsset ? (jobIdByAsset.current[effectiveAsset] ?? null) : null

  // shouldFetch: true if a jobId exists for the current asset
  // (means compute was already triggered for this asset)
  const [fetchedAssets, setFetchedAssets] = useState<Set<string>>(new Set())
  const shouldFetch = fetchedAssets.has(effectiveAsset ?? '')

  const selectedRunId = effectiveAsset ? (assetRunIds?.[effectiveAsset] ?? null) : null

  const compute = useRegimeAttributionCompute()

  const { data: jobStatus } = useRegimeAttributionJobStatus(shouldFetch ? jobId : null)

  const { data: selectedData } = useRegimeAttributionJobResult(
    jobId,
    jobStatus?.status === 'complete'
  )

  const isComputing =
    shouldFetch && jobStatus?.status !== 'complete' && jobStatus?.status !== 'failed'

  function handleAssetChange(asset: string) {
    setSelectedAsset(asset)
    // jobIdByAsset and fetchedAssets persist — switching back
    // to a previously computed asset restores the cached result
  }

  function handleCompute() {
    if (!selectedRunId || !effectiveAsset) return
    compute.mutate(
      { run_id: selectedRunId, asset: effectiveAsset, n_contracts: 4 },
      {
        onSuccess: (data) => {
          jobIdByAsset.current[effectiveAsset] = data.job_id
          setFetchedAssets((prev) => new Set([...prev, effectiveAsset]))
        },
      }
    )
  }

  // Guard: portfolio run predates asset_run_ids (pre-3abb078)
  if (!assetRunIds || availableAssets.length === 0) {
    return (
      <div className="rounded border border-border-default bg-bg-panel p-6 text-center">
        <p className="text-sm font-medium text-text-primary">Regime attribution unavailable</p>
        <p className="mt-1 text-xs text-text-secondary">
          This portfolio run was created before per-asset run IDs were recorded. Re-run the
          portfolio analysis to enable regime attribution.
        </p>
      </div>
    )
  }

  const coverage = selectedData?.regime_coverage ?? {}
  const totalDays = selectedData?.total_days_in_run ?? 0
  const daysWithData = selectedData?.total_days_with_regime ?? 0

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-text-secondary">Asset</span>
        <select
          aria-label="Select asset for regime attribution"
          value={effectiveAsset}
          onChange={(e) => handleAssetChange(e.target.value)}
          className="rounded border border-border-strong bg-bg-raised px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
        >
          {availableAssets.map((a) => (
            <option key={a} value={a}>
              {displayName(a)}
              {shouldFetch && selectedData && effectiveAsset === a && selectedData.dominant_regime
                ? ` — ${capitalize(selectedData.dominant_regime)}`
                : shouldFetch && isComputing && effectiveAsset === a
                  ? ' — loading…'
                  : ''}
            </option>
          ))}
        </select>
        {isComputing && (
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span>
              {jobStatus?.status === 'queued'
                ? 'Queued — waiting for compute slot…'
                : 'Computing regime attribution…'}
            </span>
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="About regime attribution"
                    className="inline-flex text-text-secondary transition-colors hover:text-text-primary"
                  >
                    <Info className="h-3 w-3 cursor-default" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    Classifies each trading day as contango, backwardation, or flat using the
                    futures term structure. Takes 30–90 seconds per asset.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>

      {!shouldFetch && (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <p className="text-sm text-text-secondary">
            Regime attribution classifies term structure conditions across the full price history.
            This computation takes 30–90 seconds per asset.
          </p>
          <div className="flex justify-center">
            <Button
              variant="primary"
              onClick={handleCompute}
              disabled={!selectedRunId || compute.isPending}
              className="px-6 text-sm"
            >
              Compute Regime Attribution
            </Button>
          </div>
        </div>
      )}

      {selectedData && (
        <>
          <RegimeBreakdownChart data={selectedData} loading={false} />

          <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
            <span>
              {daysWithData.toLocaleString()} of {totalDays.toLocaleString()} days had regime data
            </span>
            {Object.keys(coverage).length > 0 && (
              <>
                <span>·</span>
                {Object.entries(coverage).map(([regime, fraction]) => (
                  <span
                    key={regime}
                    className={`font-medium ${REGIME_TEXT_CLASS[regime] ?? 'text-text-secondary'}`}
                  >
                    {capitalize(regime)} {pct(fraction, 0)}
                  </span>
                ))}
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
