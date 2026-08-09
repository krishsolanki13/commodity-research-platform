/**
 * PortfolioRegimePanel — per-asset regime attribution for a portfolio run.
 *
 * Lazy single-asset fetch via useRegimeAttribution (staleTime: Infinity).
 * Parallel prefetch lives in useRegimeAttributionParallel.ts — see TD-FEP-REGIME-ASYNC.
 */
import { useMemo, useState } from 'react'
import { Info } from 'lucide-react'
import { useRegimeAttribution } from '@/api/hooks/useRegimeAttribution'
import { RegimeBreakdownChart } from '@/components/charts/RegimeBreakdownChart'
import { displayName } from '@/lib/commodity'
import { pct } from '@/lib/fmt'
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

export function PortfolioRegimePanel({
  runId: _runId,
  assetRunIds,
}: PortfolioRegimePanelProps) {
  const availableAssets = useMemo(
    () =>
      Object.entries(assetRunIds ?? {})
        .filter(([, id]) => id !== null)
        .map(([asset]) => asset)
        .sort(),
    [assetRunIds],
  )

  // Selected asset state — default to first alphabetically
  const defaultAsset = availableAssets[0] ?? ''
  const [selectedAsset, setSelectedAsset] = useState<string>('')
  const effectiveAsset = selectedAsset || defaultAsset

  const selectedRunId = effectiveAsset
    ? (assetRunIds?.[effectiveAsset] ?? null)
    : null

  const { data: selectedData, isLoading: selectedLoading } =
    useRegimeAttribution(selectedRunId, 4)

  // Guard: portfolio run predates asset_run_ids (pre-3abb078)
  if (!assetRunIds || availableAssets.length === 0) {
    return (
      <div className="rounded border border-border-default bg-bg-panel p-6 text-center">
        <p className="text-sm font-medium text-text-primary">
          Regime attribution unavailable
        </p>
        <p className="mt-1 text-xs text-text-secondary">
          This portfolio run was created before per-asset run IDs were recorded.
          Re-run the portfolio analysis to enable regime attribution.
        </p>
      </div>
    )
  }

  const coverage = selectedData?.regime_coverage ?? {}
  const totalDays = selectedData?.total_days_in_run ?? 0
  const daysWithData = selectedData?.total_days_with_regime ?? 0

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs uppercase tracking-wider text-text-secondary">
          Asset
        </span>
        <select
          value={effectiveAsset}
          onChange={(e) => setSelectedAsset(e.target.value)}
          className="rounded border border-border-strong bg-bg-raised px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
        >
          {availableAssets.map((a) => (
            <option key={a} value={a}>
              {displayName(a)}
              {selectedData && effectiveAsset === a && selectedData.dominant_regime
                ? ` — ${capitalize(selectedData.dominant_regime)}`
                : selectedLoading && effectiveAsset === a
                  ? ' — loading…'
                  : ''}
            </option>
          ))}
        </select>
        {selectedLoading && (
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <span>Computing regime attribution…</span>
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="About regime attribution"
                    className="inline-flex text-text-secondary transition-colors hover:text-text-primary"
                  >
                    <Info className="h-3.5 w-3.5 cursor-default" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs font-mono text-xs">
                    Classifies each trading day as contango, backwardation, or
                    flat using the futures term structure. Takes 30–90 seconds
                    per asset.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>

      <RegimeBreakdownChart
        data={selectedData!}
        loading={selectedLoading || !selectedData}
      />

      {selectedData && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
          <span>
            {daysWithData.toLocaleString()} of {totalDays.toLocaleString()} days
            had regime data
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
      )}
    </div>
  )
}
