/**
 * RunArtifactsTab — provenance, run parameters, signal evaluation summary.
 */
import { useRunDetail } from '@/api/hooks'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { Panel } from '@/ui/Panel'
import { fmt } from '@/lib/fmt'

interface RunArtifactsTabProps {
  runId: string
}

export function RunArtifactsTab({ runId }: RunArtifactsTabProps) {
  const runQuery = useRunDetail(runId)
  const run = runQuery.data

  if (runQuery.isError) {
    return <ErrorState error={runQuery.error ?? new Error('Failed to load run')} />
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Section 1 — Provenance */}
      <Panel title="Provenance">
        {runQuery.isLoading || !run ? (
          <LoadingSkeleton variant="form" />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-center">
              <span className="font-mono text-text-accent">{run.provenance.git_sha}</span>
              {run.provenance.dirty_flag && (
                <span className="ml-2 text-xs text-warn">⚠ dirty working tree</span>
              )}
            </div>
            <div className="flex flex-col gap-1">
              {Object.entries(run.provenance.package_versions).map(([pkg, ver]) => (
                <div key={pkg} className="flex gap-4 font-mono text-xs">
                  <span className="text-text-secondary">{pkg}</span>
                  <span className="text-text-primary">{ver}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {/* Section 2 — Run Parameters */}
      <Panel title="Run Parameters">
        {runQuery.isLoading || !run ? (
          <LoadingSkeleton variant="form" />
        ) : (
          <pre className="max-h-96 overflow-auto rounded-sm bg-bg-raised p-4 font-mono text-xs text-text-primary">
            {JSON.stringify(run.params, null, 2)}
          </pre>
        )}
      </Panel>

      {/* Section 3 — Signal Evaluation */}
      <Panel title="Signal Evaluation">
        {runQuery.isLoading || !run ? (
          <LoadingSkeleton variant="form" />
        ) : run.signal_evaluation === null ? (
          <p className="font-mono text-xs text-text-secondary">
            IC Gate override — signal_evaluation: null
          </p>
        ) : (
          <div className="flex flex-col gap-1 font-mono text-xs text-text-secondary">
            <span>IC: {run.signal_evaluation.ic?.toFixed(4) ?? '—'}</span>
            <span>ICIR: {run.signal_evaluation.icir?.toFixed(4) ?? '—'}</span>
            <span>Band: {run.signal_evaluation.ic_band}</span>
            <span>Evaluated: {fmt.isoDate(run.signal_evaluation.computed_at)}</span>
          </div>
        )}
      </Panel>
    </div>
  )
}
