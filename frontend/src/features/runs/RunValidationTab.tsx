/**
 * RunValidationTab — launch walk-forward validation and render report.
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
    <div className="space-y-4 p-4">
      {/* Launch panel */}
      {!validationId && (
        <div className="space-y-4 rounded border border-border-default bg-bg-panel p-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
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
          </div>

          {parameters && (
            <div>
              <p className="mb-0.5 text-xs uppercase tracking-wider text-text-secondary">
                Parameters
              </p>
              <p className="font-mono text-xs text-text-secondary">
                {JSON.stringify(parameters)}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
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
                className="w-full rounded border border-border-strong bg-bg-raised px-2 py-1.5 font-mono text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
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
                className="w-full rounded border border-border-strong bg-bg-raised px-2 py-1.5 font-mono text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={handleLaunch}
            disabled={!canLaunch}
            className="w-full rounded bg-amber-500 px-4 py-2 text-sm font-medium text-gray-950 hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {launch.isPending ? 'Launching…' : 'Launch Walk-Forward Validation'}
          </button>
        </div>
      )}

      {/* Polling */}
      {isPolling && (
        <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
          <p className="text-sm text-text-secondary">Running validation…</p>
        </div>
      )}

      {/* Failed */}
      {status?.status === 'failed' && (
        <div className="rounded border border-border-default bg-bg-panel px-4 py-3">
          <p className="text-sm text-loss">
            Validation failed
            {status.error ? `: ${status.error}` : '. Check the API logs for details.'}
          </p>
        </div>
      )}

      {/* Results */}
      {report && (
        <div className="space-y-4">
          <WalkForwardChart folds={folds} />
          <ValidationSummaryTable report={report} />
        </div>
      )}
    </div>
  )
}
