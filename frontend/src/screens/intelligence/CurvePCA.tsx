import { useEffect, useMemo, useState } from 'react'
import { z } from 'zod'
import { displayName } from '@/lib/commodity'
import { useUrlState } from '@/lib/useUrlState'
import { useCurveAvailableAssets } from '@/api/hooks/useCurveAvailableAssets'
import { useAssets, useCurvePCA, useCurveCoverage } from '@/api/hooks'
import { ApiClientError } from '@/api/client'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { ScreePlot } from '@/components/charts/ScreePlot'
import { PCLoadingsChart } from '@/components/charts/PCLoadingsChart'
import { PCTimeSeriesChart } from '@/components/charts/PCTimeSeriesChart'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

function coverageBoundaryDate(e: ApiClientError): string | null {
  if (e.apiError.detail && /^\d{4}-\d{2}-\d{2}$/.test(e.apiError.detail)) {
    return e.apiError.detail
  }
  const dates = `${e.apiError.message} ${e.apiError.detail ?? ''}`.match(/\d{4}-\d{2}-\d{2}/g)
  return dates?.[dates.length - 1] ?? null
}

const pcaSchema = z.object({
  asset: z.string().optional(),
  n_components: z.coerce.number().int().min(2).max(3).default(3),
  n_contracts: z.coerce.number().int().min(3).max(6).default(4),
  from_date: z.string().optional(),
  to_date: z.string().optional(),
})

const pcaDefaults = {
  n_components: 3,
  n_contracts: 4,
}

export function CurvePCA() {
  const [urlState, setUrlState] = useUrlState(pcaSchema, pcaDefaults)
  const asset = urlState.asset ?? null
  const nComponents = urlState.n_components
  const nContracts = urlState.n_contracts
  const fromDate = urlState.from_date
  const toDate = urlState.to_date

  const [submitted, setSubmitted] = useState(false)

  const { data: available, isLoading: availableLoading } = useCurveAvailableAssets()
  const { data: assetsData } = useAssets()

  const { data: pca, isLoading, error: pcaError, isError: pcaIsError } = useCurvePCA(
    submitted ? asset : null,
    nComponents,
    nContracts,
    fromDate,
    toDate
  )

  const { data: coverage } = useCurveCoverage(asset, 'carry')
  const coverageStart =
    typeof coverage?.curve_coverage_start === 'string'
      ? coverage.curve_coverage_start
      : undefined

  useEffect(() => {
    if (!coverageStart) return
    if (fromDate && fromDate < coverageStart) {
      setUrlState({ from_date: coverageStart })
    }
  }, [coverageStart, fromDate, setUrlState])

  const coverageError =
    pcaIsError && pcaError instanceof ApiClientError && pcaError.apiError.code === 'INSUFFICIENT_CURVE_COVERAGE'
      ? `Curve data for ${asset || 'this asset'} starts ${coverageBoundaryDate(pcaError) ?? 'the coverage start'} — adjust date range`
      : null

  const assetMetaMap = useMemo(() => {
    const map = new Map<string, AssetMetadata>()
    assetsData?.assets?.forEach((a) => map.set(a.name, a))
    return map
  }, [assetsData])

  const assetOptions: AssetMetadata[] = (available?.assets ?? []).map((name) => {
    const meta = assetMetaMap.get(name)
    return {
      name,
      display_name: meta?.display_name ?? displayName(name),
      ticker_continuous: meta?.ticker_continuous ?? '',
      contract_root: meta?.contract_root ?? '',
      exchange_suffix: meta?.exchange_suffix ?? '',
      exchange: meta?.exchange ?? '',
      currency: meta?.currency ?? 'USD',
      unit: meta?.unit ?? '',
      contract_multiplier: meta?.contract_multiplier ?? 1,
      tick_size: meta?.tick_size ?? 0.01,
      tick_value: meta?.tick_value ?? 1,
    }
  })

  useEffect(() => {
    setSubmitted(false)
  }, [asset])

  function handleNewAnalysis() {
    setSubmitted(false)
    setUrlState({
      asset: null,
      n_components: 3,
      n_contracts: 4,
      from_date: null,
      to_date: null,
    })
  }

  if (pca != null) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="shrink-0 px-6 pb-4 pt-6">
          <h1 className="text-xl font-semibold text-text-primary">Curve PCA</h1>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6">
          <button
            type="button"
            onClick={handleNewAnalysis}
            className="flex w-fit items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
          >
            ← New Analysis
          </button>

          <ScreePlot
            evr={pca.explained_variance_ratio}
            cumEvr={pca.cumulative_variance_ratio}
            pcLabels={pca.pc_labels}
          />
          <PCLoadingsChart loadings={pca.loadings} nContracts={nContracts} />
          <PCTimeSeriesChart
            factorSeries={pca.factor_series}
            indexEpochMs={pca.factor_index_epoch_ms}
            pcLabels={pca.pc_labels}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pb-4 pt-6">
        <h1 className="text-xl font-semibold text-text-primary">Curve PCA</h1>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
        <div className="min-h-0 overflow-y-auto">
          <Panel title="PCA Configuration">
            <div className="flex flex-col gap-4">
              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Asset
                </span>
                <AssetSelector
                  value={asset}
                  onChange={(v) => setUrlState({ asset: v ?? null })}
                  assets={assetOptions}
                  aria-label="Select commodity asset"
                />
              </div>

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Components
                </span>
                <Select
                  value={String(nComponents)}
                  onValueChange={(v) => setUrlState({ n_components: Number(v) })}
                  disabled={availableLoading}
                >
                  <SelectTrigger
                    className="w-full font-mono text-sm"
                    aria-label="Number of principal components"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 3].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n} components
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Contracts
                </span>
                <Select
                  value={String(nContracts)}
                  onValueChange={(v) => setUrlState({ n_contracts: Number(v) })}
                  disabled={availableLoading}
                >
                  <SelectTrigger
                    className="w-full font-mono text-sm"
                    aria-label="Number of contracts"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[3, 4, 5, 6].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n} contracts
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Date Range
                </span>
                <div className="flex items-center gap-2">
                  <input
                    type="date"
                    value={fromDate ?? ''}
                    min={coverageStart}
                    onChange={(e) => setUrlState({ from_date: e.target.value || null })}
                    className="py-1.5 rounded border border-border-strong bg-bg-raised px-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
                    aria-label="From date"
                  />
                  <span className="text-xs text-text-secondary">→</span>
                  <input
                    type="date"
                    value={toDate ?? ''}
                    onChange={(e) => setUrlState({ to_date: e.target.value || null })}
                    className="py-1.5 rounded border border-border-strong bg-bg-raised px-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
                    aria-label="To date"
                  />
                </div>
                {coverageStart && (
                  <p className="font-mono text-xs text-warn">
                    Curve data for {asset} available from {coverageStart}
                  </p>
                )}
                <p className="text-xs text-text-disabled">Optional</p>
              </div>
            </div>
          </Panel>
        </div>

        <div className="min-h-0 overflow-y-auto">
          <Panel title="View">
            <div className="flex flex-col gap-4">
              <Button
                variant="primary"
                className="w-full"
                disabled={!asset || isLoading}
                onClick={() => setSubmitted(true)}
              >
                View PCA
              </Button>

              {!asset && (
                <p className="text-xs text-text-secondary">Select an asset to run curve PCA</p>
              )}

              {coverageError && (
                <div
                  role="alert"
                  className="rounded border border-loss bg-loss-fill px-3 py-2 text-sm text-loss"
                >
                  {coverageError}
                </div>
              )}

              {submitted && !coverageError && (
                <p className="mt-4 text-center text-sm text-text-secondary">
                  Computing PCA — this may take a moment…
                </p>
              )}

              {!submitted && asset && (
                <p className="text-xs text-text-secondary">
                  Select an asset and click View PCA to analyze forward curve principal components.
                </p>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

export default CurvePCA
