/**
 * RunSignalQualityTab — signal evaluation metrics and IC decay chart.
 *
 * Rolling IC chart deferred — no rolling IC series endpoint available yet.
 * When backend adds /api/signals/rolling-ic, wire the rolling IC chart here.
 */
import { useRunDetail } from '@/api/hooks'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { ICBandBadge } from '@/components/data/ICBandBadge'
import { MetricGrid } from '@/components/data/MetricGrid'
import { EmptyState } from '@/components/layout/EmptyState'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { Panel } from '@/ui/Panel'

interface RunSignalQualityTabProps {
  runId: string
}

export function RunSignalQualityTab({ runId }: RunSignalQualityTabProps) {
  const runQuery = useRunDetail(runId)
  const run = runQuery.data

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
        <div className="flex h-48 flex-col items-center justify-center gap-2 px-6 text-center text-sm text-text-secondary">
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
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <ICBandBadge ic={evaluation.ic} />
        <MetricGrid
          columns={3}
          metrics={[
            { label: 'IC', value: evaluation.ic, format: 'ic', tone: 'neutral' },
            { label: 'ICIR', value: evaluation.icir, format: 'ic', tone: 'neutral' },
            { label: 'TURNOVER', value: evaluation.turnover, format: 'percent', tone: 'neutral' },
          ]}
        />
      </div>

      <ICDecayChart decay={evaluation.decay} height={250} title="IC Decay at Horizons" />

      {/* Rolling IC chart deferred — no rolling IC series endpoint available yet. */}
      <Panel title="Rolling IC">
        <EmptyState
          title="Rolling IC chart pending"
          body="Awaiting backend /api/signals/rolling-ic endpoint. Rolling IC chart will be wired when the endpoint ships."
        />
      </Panel>
    </div>
  )
}
