import { useMemo } from 'react'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'
import { EmptyState } from '@/components/layout/EmptyState'
import { SignalOverlayChart } from '@/components/charts/SignalOverlayChart'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { MetricGrid } from '@/components/data/MetricGrid'
import { FeatureSpecTable } from '@/components/data/FeatureSpecTable'
import type { MetricStatProps } from '@/components/data/MetricStat'
import type { components } from '@/api/schema'
import { RegimeContextChip } from '@/features/intelligence/RegimeContextChip'

type FeatureComputeResponse = components['schemas']['FeatureComputeResponse']
type SignalGenerateResponse = components['schemas']['SignalGenerateResponse']
type SignalEvaluateResponse = components['schemas']['SignalEvaluateResponse']
type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']
type ColumnarSeries = components['schemas']['ColumnarSeries']

export interface WorkbenchEvaluationResult {
  features: FeatureComputeResponse
  signal: SignalGenerateResponse
  evaluation: SignalEvaluateResponse
  evaluatedAt: string
}

interface WorkbenchEvidenceCanvasProps {
  asset: string
  strategy: string
  params: Record<string, unknown>
  featureSpecs: FeatureSpecRequest[]
  fromDate: string
  toDate: string
  lastEvaluatedConfigHash: string | null
  evaluationResult: WorkbenchEvaluationResult | null
}

const EMPTY_SERIES: ColumnarSeries = { index: [], columns: {} }

/**
 * Evidence canvas for the Research Workbench.
 *
 * Architectural note (§9 constraint 10): ICRollingChart is NOT used here.
 * SignalEvaluateResponse only returns IC decay at fixed horizons, not a rolling
 * IC time series. ICRollingChart is reserved for F6 Run Detail Signal Quality tab.
 */
export function WorkbenchEvidenceCanvas({
  asset,
  strategy,
  params,
  featureSpecs,
  fromDate,
  toDate,
  lastEvaluatedConfigHash,
  evaluationResult,
}: WorkbenchEvidenceCanvasProps) {
  const currentConfigHash = useMemo(
    () => JSON.stringify({ asset, strategy, params, featureSpecs, fromDate, toDate }),
    [asset, strategy, params, featureSpecs, fromDate, toDate]
  )
  const isStale = lastEvaluatedConfigHash !== null && currentConfigHash !== lastEvaluatedConfigHash

  const { data: ohlcv, isLoading: ohlcvLoading } = useAssetOhlcv(asset, {
    from_date: fromDate,
    to_date: toDate,
    downsample: 'view',
  })

  if (!evaluationResult) {
    return (
      <EmptyState
        title="Evaluate to see results"
        body="Assemble features and a signal, then click Evaluate. Evaluation must precede backtesting."
      />
    )
  }

  const evalData = evaluationResult.evaluation.evaluation

  const metrics: MetricStatProps[] = [
    { label: 'IC', value: evalData.ic, format: 'ic' },
    { label: 'ICIR', value: evalData.icir, format: 'ic' },
    { label: 'TURNOVER', value: evalData.turnover, format: 'percent' },
    {
      label: 'EVAL WINDOW',
      value: evalData.evaluation_window,
      format: 'integer',
      tone: 'neutral',
      hint: 'bars',
    },
  ]

  const priceSeries = ohlcv?.data ?? evaluationResult.signal.raw_signal ?? EMPTY_SERIES

  return (
    <div className="relative min-h-full">
      {isStale && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-start justify-center">
          <div className="py-1.5 pointer-events-auto mt-8 flex items-center gap-2 rounded-md border border-warn bg-bg-raised px-3 text-xs text-warn opacity-100">
            Configuration changed — re-evaluate
          </div>
        </div>
      )}
      <div className={isStale ? 'pointer-events-none opacity-60' : ''}>
        <div className="flex flex-col gap-6">
          {/* Regime context — supplementary intelligence; renders null if no curve data */}
          <div className="mb-4">
            <RegimeContextChip asset={asset} compact={false} />
          </div>

          <SignalOverlayChart
            ohlcv={priceSeries}
            raw={evaluationResult.signal.raw_signal}
            position={evaluationResult.signal.position_signal}
            title={`Signal — ${asset} · ${strategy}`}
            syncGroup="workbench"
            height="45vh"
            loading={ohlcvLoading}
          />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ICDecayChart decay={evalData.decay} height={200} title="IC Decay" />
            <MetricGrid metrics={metrics} columns={4} className="w-full" />
          </div>

          <FeatureSpecTable specs={evaluationResult.features.specs} className="w-full" />
        </div>
      </div>
    </div>
  )
}
