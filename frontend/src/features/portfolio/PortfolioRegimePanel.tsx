/**
 * PortfolioRegimePanel — per-asset regime attribution for a portfolio run.
 *
 * Prefetches regime attribution for all assets in parallel via useQueries so
 * dropdown switches hit the TanStack Query cache (staleTime: Infinity).
 */
import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { RegimeBreakdownChart } from '@/components/charts/RegimeBreakdownChart'
import { displayName } from '@/lib/commodity'
import { pct } from '@/lib/fmt'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

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

  // Prefetch all assets in parallel on mount
  const regimeQueries = useQueries({
    queries: availableAssets.map((asset) => {
      const assetRunId = assetRunIds?.[asset] ?? null
      const qs = new URLSearchParams({ n_contracts: '4' })
      return {
        queryKey: qk.regimeAttribution(assetRunId!, 4),
        queryFn: (): Promise<RegimeAttributionResponse> =>
          client.get(`/api/runs/${assetRunId}/regime-attribution?${qs}`),
        enabled: !!assetRunId,
        staleTime: Infinity,
      }
    }),
  })

  // Build a lookup map: asset → { data, isLoading }
  const regimeByAsset = useMemo(
    () =>
      Object.fromEntries(
        availableAssets.map((asset, i) => [
          asset,
          {
            data: regimeQueries[i]?.data ?? null,
            isLoading: regimeQueries[i]?.isLoading ?? false,
          },
        ]),
      ),
    [availableAssets, regimeQueries],
  )

  // Selected asset state — default to first alphabetically
  const defaultAsset = availableAssets[0] ?? ''
  const [selectedAsset, setSelectedAsset] = useState<string>('')
  const effectiveAsset = selectedAsset || defaultAsset

  // Read selected asset data from the parallel query map
  const selectedData = regimeByAsset[effectiveAsset]?.data ?? null
  const selectedLoading = regimeByAsset[effectiveAsset]?.isLoading ?? false

  // Overall loading: any assets still loading (for the hint text)
  const anyLoading = regimeQueries.some((q) => q.isLoading)
  const loadedCount = regimeQueries.filter((q) => q.isSuccess).length

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
          {availableAssets.map((a) => {
            const aData = regimeByAsset[a]
            const assetDominant = aData?.data?.dominant_regime
            const loading = aData?.isLoading
            return (
              <option key={a} value={a}>
                {displayName(a)}
                {assetDominant
                  ? ` — ${capitalize(assetDominant)}`
                  : loading
                    ? ' — loading…'
                    : ''}
              </option>
            )
          })}
        </select>
        {anyLoading && (
          <span className="text-xs text-text-secondary">
            {loadedCount}/{availableAssets.length} assets loaded
          </span>
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
