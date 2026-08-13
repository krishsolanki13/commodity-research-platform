/**
 * RunSignalQualityTab — signal evaluation metrics, IC decay, and rolling IC.
 */
import { useRunDetail, useRollingIC } from '@/api/hooks'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { ICRollingChart } from '@/components/charts/ICRollingChart'
import { MetricStat } from '@/components/data/MetricStat'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { Panel } from '@/ui/Panel'
import type { components } from '@/api/schema'

type ColumnarSeries = components['schemas']['ColumnarSeries']

const EMPTY_SERIES: ColumnarSeries = { index: [], columns: {} }

interface RunSignalQualityTabProps {
  runId: string
}

export function RunSignalQualityTab({ runId }: RunSignalQualityTabProps) {
  const runQuery = useRunDetail(runId)
  const run = runQuery.data

  const strategyParams =
    (run?.params as { parameters?: Record<string, unknown> } | undefined)?.parameters ?? null

  const { data: rollingIcData, isLoading: rollingIcLoading } = useRollingIC(
    run?.asset ?? null,
    run?.strategy ?? null,
    strategyParams,
    63
  )

  if (runQuery.isLoading) {
    return <LoadingSkeleton variant="metric-grid" columns={3} />
  }

  if (runQuery.isError) {
    return <ErrorState error={runQuery.error ?? new Error('Failed to load run')} />
  }

  const evaluation = run?.signal_evaluation

  // STATE A — IC Gate override / no evaluation recorded (backend gap: POST
  // /api/backtest/run does not yet persist signal_evaluation for all launches)
  if (evaluation === null || evaluation === undefined) {
    return (
      <Panel title="Signal Quality">
        <div className="h-48 flex flex-col items-center justify-center gap-2 px-6 text-center text-sm text-text-secondary">
          <span className="text-2xl text-text-disabled">~</span>
          <span className="font-medium">No signal evaluation recorded</span>
          <span className="text-xs leading-relaxed text-text-disabled">
            Launch this backtest from the Research Workbench after evaluating the signal to record
            IC quality here.
          </span>
          <a
            href={`/research?asset=${run?.asset ?? ''}&strategy=${run?.strategy ?? ''}`}
            className="mt-2 text-xs text-text-accent hover:underline"
          >
            Open Workbench →
          </a>
        </div>
      </Panel>
    )
  }

  // STATE B — signal_evaluation present
  const icBand = evaluation.ic_band

  // RollingICResponse.data.columns.rolling_ic → ICRollingChart ic.columns.value
  const icSeries: ColumnarSeries = rollingIcData?.data
    ? {
        index: rollingIcData.data.index,
        columns: { value: rollingIcData.data.columns.rolling_ic ?? [] },
      }
    : EMPTY_SERIES

  return (
    <div className="flex flex-col gap-6">
      <div className="grid w-full grid-cols-3 gap-4">
        <div className="gap-0.5 flex flex-col">
          <MetricStat label="IC" value={evaluation.ic} format="ic" tone="auto" />
          {icBand && <span className="pl-0 font-mono text-xs text-text-secondary">{icBand}</span>}
        </div>
        <MetricStat label="ICIR" value={evaluation.icir} format="ic" tone="neutral" />
        <MetricStat label="TURNOVER" value={evaluation.turnover} format="percent" tone="neutral" />
      </div>

      <ICDecayChart decay={evaluation.decay} height={250} title="IC Decay at Horizons" />

      <ICRollingChart
        ic={icSeries}
        window={rollingIcData?.window ?? 63}
        title="Rolling IC"
        height={250}
        loading={rollingIcLoading || !rollingIcData}
      />
    </div>
  )
}
