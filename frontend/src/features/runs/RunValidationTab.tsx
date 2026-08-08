/**
 * RunValidationTab — launch walk-forward validation and render report.
 *
 * Layout matches FuturesCurve (TDR-015): grid-cols-2 config | action+results.
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

interface RunValidationTabProps {
  // Passed from RunDetail — avoids duplicate fetch of run metadata
  // run.asset, run.strategy (NOT run.strategy_name — F16 confirmed), run.params
  asset: string | null
  strategyName: string | null
  parameters: Record<string, unknown> | null
}

export function RunValidationTab({
  asset,
  strategyName,
  parameters,
}: RunValidationTabProps) {
  const [validationId, setValidationId] = useState<string | null>(null)
  const [nSplits, setNSplits] = useState(5)
  const [embargoBars, setEmbargoBars] = useState(10)

  const launch = useValidationLaunch()
  const { data: status } = useValidationStatus(validationId)
  const { data: report } = useValidationReport(
    status?.status === 'complete' ? validationId : null,
  )

  const isPolling = status?.status === 'queued' || status?.status === 'running'
  const canLaunch =
    !!asset && !!strategyName && !!parameters && !launch.isPending && !validationId

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
      },
    )
  }

  // Map WalkForwardFoldResponse → WalkForwardChart fold shape
  const folds =
    report?.folds.map((f) => ({
      fold: f.split.fold_idx,
      is_sharpe: f.train_sharpe,
      oos_sharpe: f.test_sharpe,
    })) ?? []

  return (
    <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden">
      {/* Left — config (read-only metadata + editable inputs) */}
      <div className="min-h-0 overflow-y-auto">
        <Panel title="Configuration">
          <div className="flex flex-col gap-4">
            <div>
              <p className="mb-0.5 text-xs uppercase tracking-wider text-text-secondary">
                Asset
              </p>
              <p className="font-mono text-text-primary">{asset ?? '—'}</p>
            </div>
            <div>
              <p className="mb-0.5 text-xs uppercase tracking-wider text-text-secondary">
                Strategy
              </p>
              <p className="font-mono text-text-primary">{strategyName ?? '—'}</p>
            </div>
            {parameters && (
              <div>
                <p className="mb-0.5 text-xs uppercase tracking-wider text-text-secondary">
                  Parameters
                </p>
                <p className="font-mono text-xs text-text-secondary">
                  {Object.entries(parameters)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' · ')}
                </p>
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs text-text-secondary">
                Walk-forward splits
              </label>
              <input
                type="number"
                min={2}
                max={20}
                value={nSplits}
                onChange={(e) => setNSplits(Math.max(2, Number(e.target.value)))}
                disabled={!!validationId}
                className="w-full rounded border border-border-strong bg-bg-raised px-2 py-1.5 font-mono text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring disabled:opacity-50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">
                Embargo bars
              </label>
              <input
                type="number"
                min={0}
                max={63}
                value={embargoBars}
                onChange={(e) =>
                  setEmbargoBars(Math.max(0, Number(e.target.value)))
                }
                disabled={!!validationId}
                className="w-full rounded border border-border-strong bg-bg-raised px-2 py-1.5 font-mono text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring disabled:opacity-50"
              />
            </div>
          </div>
        </Panel>
      </div>

      {/* Right — launch + results */}
      <div className="min-h-0 overflow-y-auto">
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

            {!validationId && (
              <p className="text-xs text-text-secondary">
                Launch walk-forward validation to compare in-sample vs out-of-sample
                Sharpe across folds.
              </p>
            )}

            {isPolling && (
              <p className="text-sm text-text-secondary">
                Running validation ({nSplits} folds)…
              </p>
            )}

            {status?.status === 'failed' && (
              <p className="text-sm text-loss">
                Validation failed
                {status.error ? `: ${status.error}` : '. Check the API logs for details.'}
              </p>
            )}

            {report && (
              <div className="flex flex-col gap-4">
                <WalkForwardChart folds={folds} />
                <ValidationSummaryTable report={report} />
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  )
}
