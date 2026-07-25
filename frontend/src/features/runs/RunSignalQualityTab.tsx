/**
 * RunSignalQualityTab — signal evaluation metrics and IC decay chart.
 *
 * Rolling IC chart deferred — no rolling IC series endpoint available yet.
 * When backend adds /api/signals/rolling-ic, wire the rolling IC chart here.
 */
import { useRunDetail } from '@/api/hooks'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { MetricStat } from '@/components/data/MetricStat'
import { EmptyState } from '@/components/layout/EmptyState'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { Panel } from '@/ui/Panel'
import { cn } from '@/lib/cn'

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

  return (
    <div className="flex flex-col gap-6">
      <div className="grid w-full grid-cols-3 gap-4">
        <div className="gap-0.5 flex min-w-0 flex-col">
          <span className="text-xs uppercase tracking-wider text-text-secondary">IC</span>
          <div className="flex flex-col items-start">
            <span className="text-2xl font-mono">
              {evaluation.ic != null ? evaluation.ic.toFixed(3) : '—'}
            </span>
            {icBand != null && (
              <span
                className={cn(
                  'mt-0.5 px-1.5 py-0.5 rounded font-mono text-xs',
                  icBand === 'strong' || icBand === 'inverse_meaningful'
                    ? 'bg-gain-fill text-gain'
                    : icBand === 'noise'
                      ? 'bg-bg-raised text-text-secondary'
                      : 'bg-accent-fill text-warn'
                )}
              >
                {icBand}
              </span>
            )}
          </div>
        </div>
        <MetricStat label="ICIR" value={evaluation.icir} format="ic" tone="neutral" />
        <MetricStat label="TURNOVER" value={evaluation.turnover} format="percent" tone="neutral" />
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
