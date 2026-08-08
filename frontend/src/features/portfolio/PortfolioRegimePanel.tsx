/**
 * PortfolioRegimePanel — per-asset regime attribution for a portfolio run.
 *
 * Selects an underlying asset run via asset_run_ids, fetches regime attribution,
 * and renders RegimeBreakdownChart + coverage summary.
 */
import { useEffect, useState } from 'react'
import { useRegimeAttribution } from '@/api/hooks/useRegimeAttribution'
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

const EMPTY_REGIME: RegimeAttributionResponse = {
  run_id: '',
  asset: '',
  strategy_name: '',
  n_contracts: 4,
  computation_date: '',
  regime_metrics: {},
  regime_coverage: {},
  dominant_regime: '',
  total_days_with_regime: 0,
  total_days_in_run: 0,
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1)
}

export function PortfolioRegimePanel({
  runId: _runId,
  assetRunIds,
}: PortfolioRegimePanelProps) {
  const availableAssets = Object.entries(assetRunIds ?? {})
    .filter(([, id]) => id !== null)
    .map(([asset]) => asset)
    .sort()

  const [selectedAsset, setSelectedAsset] = useState<string>('')

  // assetRunIds arrives async from the parent query — seed default once available
  useEffect(() => {
    if (!selectedAsset && availableAssets.length > 0) {
      setSelectedAsset(availableAssets[0] ?? '')
    }
  }, [availableAssets, selectedAsset])

  const selectedRunId = selectedAsset
    ? (assetRunIds?.[selectedAsset] ?? null)
    : null

  const { data, isLoading } = useRegimeAttribution(selectedRunId, 4)

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

  const dominant = data?.dominant_regime
  const coverage = data?.regime_coverage ?? {}
  const totalDays = data?.total_days_in_run ?? 0
  const daysWithData = data?.total_days_with_regime ?? 0

  return (
    <div className="space-y-3">
      {/* Asset selector — plain <select>; PortfolioPerAssetPanel has no asset picker */}
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-text-secondary">
          Asset
        </span>
        <select
          value={selectedAsset}
          onChange={(e) => setSelectedAsset(e.target.value)}
          className="rounded border border-border-strong bg-bg-raised px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
        >
          {availableAssets.map((a) => (
            <option key={a} value={a}>
              {displayName(a)}
              {data && selectedAsset === a && dominant
                ? ` — ${capitalize(dominant)}`
                : ''}
            </option>
          ))}
        </select>
      </div>

      <RegimeBreakdownChart
        data={data ?? EMPTY_REGIME}
        loading={isLoading || !data}
      />

      {data && (
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
