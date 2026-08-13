/**
 * RunValidationTab — launch walk-forward validation and render report.
 *
 * Pre-launch: grid-cols-2 (FuturesCurve / StrategyBuilder pattern).
 * Post-launch: full-width results column (chart + table need full width).
 * Padding inherited from RunDetail (same as RunSignalQualityTab — no extra pad).
 *
 * Corrections vs draft assumptions:
 *   - Launch response uses validation_run_id (Inc1)
 *   - Folds use WalkForwardFoldResponse: split.fold_idx, train_sharpe, test_sharpe
 *   - Summary uses ValidationReportResponse flat insample_/outsample_ fields
 */
import { useState } from 'react'
import { useValidationLaunch } from '@/api/hooks/useValidationLaunch'
import { useValidationStatus } from '@/api/hooks/useValidationStatus'
import { useValidationReport } from '@/api/hooks/useValidationReport'
import { WalkForwardChart } from '@/components/charts/WalkForwardChart'
import { ValidationSummaryTable } from '@/features/runs/ValidationSummaryTable'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import { NumberInput } from '@/ui/NumberInput'

interface RunValidationTabProps {
  // Passed from RunDetail — avoids duplicate fetch of run metadata
  // run.asset, run.strategy (NOT run.strategy_name — F16 confirmed), run.params
  asset: string | null
  strategyName: string | null
  parameters: Record<string, unknown> | null
}

export function RunValidationTab({ asset, strategyName, parameters }: RunValidationTabProps) {
  const [validationId, setValidationId] = useState<string | null>(null)
  const [nSplits, setNSplits] = useState(5)
  const [embargoBars, setEmbargoBars] = useState(10)

  const launch = useValidationLaunch()
  const { data: status } = useValidationStatus(validationId)
  const { data: report } = useValidationReport(status?.status === 'complete' ? validationId : null)

  const isPolling = status?.status === 'queued' || status?.status === 'running'
  const canLaunch = !!asset && !!strategyName && !!parameters && !launch.isPending && !validationId

  function handleLaunch() {
    if (!asset || !strategyName || !parameters) return
    launch.mutate(
      {
        asset,
        strategy_name: strategyName,
        parameters,
        n_splits: nSplits,
        embargo_bars: embargoBars,
      },
      {
        onSuccess: (data) => setValidationId(data.validation_run_id),
      }
    )
  }

  // Map WalkForwardFoldResponse → WalkForwardChart fold shape
  const folds =
    report?.folds.map((f) => ({
      fold: f.split.fold_idx,
      is_sharpe: f.train_sharpe,
      oos_sharpe: f.test_sharpe,
    })) ?? []

  if (validationId === null) {
    return (
      <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden">
        {/* Left — config (FuturesCurve Configuration panel pattern) */}
        <div className="min-h-0 overflow-y-auto">
          <Panel title="Configuration">
            <div className="flex flex-col gap-4">
              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Asset
                </span>
                <p className="font-mono text-sm text-text-primary">{asset ?? '—'}</p>
              </div>
              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Strategy
                </span>
                <p className="font-mono text-sm text-text-primary">{strategyName ?? '—'}</p>
              </div>
              {parameters && (
                <div className="gap-1.5 flex flex-col">
                  <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                    Parameters
                  </span>
                  <p className="font-mono text-xs text-text-secondary">
                    {Object.entries(parameters)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(' · ')}
                  </p>
                </div>
              )}
              <div className="flex flex-col gap-1">
                <label className="text-sm text-text-secondary">Walk-forward splits</label>
                <NumberInput
                  value={nSplits}
                  onChange={(v) => setNSplits(Math.max(2, Math.min(20, v)))}
                  min={2}
                  max={20}
                  step={1}
                  aria-label="Walk-forward splits"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-sm text-text-secondary">Embargo bars</label>
                <NumberInput
                  value={embargoBars}
                  onChange={(v) => setEmbargoBars(Math.max(0, Math.min(63, v)))}
                  min={0}
                  max={63}
                  step={1}
                  aria-label="Embargo bars"
                />
              </div>
            </div>
          </Panel>
        </div>

        {/* Right — launch (FuturesCurve View panel pattern) */}
        <div className="min-h-0">
          <Panel title="Validation">
            <div className="flex flex-col gap-4">
              <Button
                variant="primary"
                disabled={!canLaunch}
                onClick={handleLaunch}
                className="w-full"
                loading={launch.isPending}
              >
                {launch.isPending ? 'Launching…' : 'Launch Walk-Forward Validation'}
              </Button>
              <p className="text-xs text-text-secondary">
                Launch walk-forward validation to compare in-sample vs out-of-sample Sharpe across
                folds.
              </p>
            </div>
          </Panel>
        </div>
      </div>
    )
  }

  // Post-launch — full-width results
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
      {isPolling && (
        <p className="text-sm text-text-secondary">Running validation ({nSplits} folds)…</p>
      )}

      {status?.status === 'failed' && (
        <p className="text-sm text-loss">
          Validation failed
          {status.error ? `: ${status.error}` : '. Check the API logs for details.'}
        </p>
      )}

      {report && (
        <>
          <WalkForwardChart folds={folds} />
          <ValidationSummaryTable report={report} />
        </>
      )}
    </div>
  )
}
