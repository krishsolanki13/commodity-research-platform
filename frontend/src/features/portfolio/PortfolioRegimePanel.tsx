/**
 * PortfolioRegimePanel — per-asset + portfolio-combined regime attribution.
 *
 * Opt-in compute via shouldFetch — does not auto-fetch on mount (avoids
 * blocking the single-worker API).
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Info } from 'lucide-react'
import {
  useRegimeAttributionCompute,
  useRegimeAttributionJobStatus,
  useRegimeAttributionJobResult,
  usePortfolioRegimeCompute,
  usePortfolioRegimeResult,
} from '@/api/hooks'
import { qk } from '@/api/queryKeys'
import { RegimeBreakdownChart } from '@/components/charts/RegimeBreakdownChart'
import { displayName } from '@/lib/commodity'
import { pct } from '@/lib/fmt'
import { Button } from '@/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

const PORTFOLIO_KEY = '__portfolio__'

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

export function PortfolioRegimePanel({ runId, assetRunIds }: PortfolioRegimePanelProps) {
  const availableAssets = useMemo(
    () =>
      Object.entries(assetRunIds ?? {})
        .filter(([, id]) => id !== null)
        .map(([asset]) => asset)
        .sort(),
    [assetRunIds]
  )

  const [selectedAsset, setSelectedAsset] = useState<string>(PORTFOLIO_KEY)
  const effectiveAsset = selectedAsset || PORTFOLIO_KEY
  const isPortfolio = effectiveAsset === PORTFOLIO_KEY

  // Map of asset → jobId, persists across asset switches
  // '__portfolio__' key stores the portfolio-combined job ID
  const jobIdByAsset = useRef<Record<string, string>>({})

  const jobId = jobIdByAsset.current[effectiveAsset] ?? null

  const [fetchedAssets, setFetchedAssets] = useState<Set<string>>(new Set())
  const shouldFetch = fetchedAssets.has(effectiveAsset)

  const selectedRunId = isPortfolio
    ? runId
    : (assetRunIds?.[effectiveAsset] ?? null)

  const computeAsset = useRegimeAttributionCompute()
  const computePortfolio = usePortfolioRegimeCompute()
  const queryClient = useQueryClient()

  const cachedResult = jobId
    ? isPortfolio
      ? queryClient.getQueryData(qk.regimeAttributionJob.portfolioResult(jobId))
      : queryClient.getQueryData(qk.regimeAttributionJob.result(jobId))
    : undefined

  const { data: jobStatus } = useRegimeAttributionJobStatus(
    shouldFetch && !cachedResult ? jobId : null
  )

  const { data: perAssetData } = useRegimeAttributionJobResult(
    isPortfolio ? null : jobId,
    !isPortfolio && (jobStatus?.status === 'complete' || !!cachedResult)
  )

  const { data: portfolioData } = usePortfolioRegimeResult(
    isPortfolio && (jobStatus?.status === 'complete' || !!cachedResult) ? jobId : null
  )

  const chartData: RegimeAttributionResponse | null = useMemo(() => {
    if (isPortfolio && portfolioData?.portfolio_regime_metrics) {
      return {
        run_id: portfolioData.portfolio_run_id,
        asset: 'portfolio',
        strategy_name: '',
        n_contracts: 4,
        computation_date: portfolioData.computation_date ?? '',
        regime_metrics: portfolioData.portfolio_regime_metrics,
        regime_coverage: Object.fromEntries(
          Object.entries(portfolioData.portfolio_regime_metrics).map(([k, v]) => [
            k,
            v.coverage ?? 0,
          ])
        ),
        dominant_regime: portfolioData.dominant_regime ?? '',
        total_days_with_regime: 0,
        total_days_in_run: 0,
      }
    }
    return perAssetData ?? null
  }, [isPortfolio, portfolioData, perAssetData])

  const selectedData = chartData

  // Hold last valid chart payload so RegimeBreakdownChart does not collapse
  // to zero height while switching assets / awaiting a new job result.
  const lastValidMetrics = useRef<RegimeAttributionResponse | null>(null)
  useEffect(() => {
    if (selectedData) {
      lastValidMetrics.current = selectedData
    }
  }, [selectedData])
  const chartMetrics = selectedData ?? lastValidMetrics.current

  const dominantRegime = isPortfolio
    ? portfolioData?.dominant_regime
    : perAssetData?.dominant_regime

  const isComputing =
    shouldFetch &&
    !selectedData &&
    jobStatus?.status !== 'complete' &&
    jobStatus?.status !== 'failed'

  function handleAssetChange(asset: string) {
    setSelectedAsset(asset)
  }

  function handleCompute() {
    if (isPortfolio) {
      if (!runId) return
      computePortfolio.mutate(
        { portfolio_run_id: runId, n_contracts: 4 },
        {
          onSuccess: (data) => {
            jobIdByAsset.current[PORTFOLIO_KEY] = data.job_id
            setFetchedAssets((prev) => new Set([...prev, PORTFOLIO_KEY]))
          },
        }
      )
      return
    }
    if (!selectedRunId || !effectiveAsset) return
    computeAsset.mutate(
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
          <option value={PORTFOLIO_KEY}>
            Portfolio Combined
            {shouldFetch && selectedData && isPortfolio && dominantRegime
              ? ` — ${capitalize(dominantRegime)}`
              : shouldFetch && isComputing && isPortfolio
                ? ' — loading…'
                : ''}
          </option>
          {availableAssets.map((a) => (
            <option key={a} value={a}>
              {displayName(a)}
              {shouldFetch && selectedData && effectiveAsset === a && dominantRegime
                ? ` — ${capitalize(dominantRegime)}`
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
            {isPortfolio
              ? 'Portfolio Combined aggregates regime attribution across all assets with P&L-weighted Sharpe. This may take several minutes.'
              : 'Regime attribution classifies term structure conditions across the full price history. This computation takes 30–90 seconds per asset.'}
          </p>
          <div className="flex justify-center">
            <Button
              variant="primary"
              onClick={handleCompute}
              disabled={
                isPortfolio
                  ? !runId || computePortfolio.isPending
                  : !selectedRunId || computeAsset.isPending
              }
              className="px-6 text-sm"
            >
              Compute Regime Attribution
            </Button>
          </div>
        </div>
      )}

      {shouldFetch && (
        <>
          <div className="flex min-h-[320px] items-center justify-center">
            {chartMetrics ? (
              <RegimeBreakdownChart data={chartMetrics} loading={false} />
            ) : (
              <span className="text-sm text-text-secondary">Computing…</span>
            )}
          </div>

          {chartMetrics && !isPortfolio && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
              <span>
                {daysWithData.toLocaleString()} of {totalDays.toLocaleString()} days had regime
                data
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
          {chartMetrics && isPortfolio && portfolioData && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
              <span>
                {portfolioData.n_assets_computed} asset
                {portfolioData.n_assets_computed === 1 ? '' : 's'} aggregated
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
        </>
      )}
    </div>
  )
}
