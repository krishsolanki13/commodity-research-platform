import { useParams, Link, Navigate } from 'react-router-dom'
import { TabsUrlSync } from '@/ui/TabsUrlSync'
import { useRunDetail } from '@/api/hooks'
import { ApiClientError } from '@/api/client'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { RunOverviewTab } from '@/features/runs/RunOverviewTab'
import { RunSignalQualityTab } from '@/features/runs/RunSignalQualityTab'
import { RunTradesTab } from '@/features/runs/RunTradesTab'
import { RunArtifactsTab } from '@/features/runs/RunArtifactsTab'
import { fmt } from '@/lib/fmt'

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const { data: run, isLoading, error } = useRunDetail(runId ?? '')

  if (!runId) return <Navigate to="/runs" replace />

  // 404 handling — show immediately (useRunDetail has retry: false for 404)
  if (
    error instanceof ApiClientError &&
    (error.apiError.code === 'RUN_NOT_FOUND' || error.apiError.status === 404)
  ) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <ErrorState error={new Error('Run not found')} />
        <Link to="/runs" className="text-xs text-text-accent hover:underline">
          ← All runs
        </Link>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-default px-6 py-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            {run && <RunStatusBadge status={run.status} />}
            <span className="max-w-xs truncate font-mono text-xs text-text-secondary" title={runId}>
              {runId}
            </span>
          </div>
          {run && (
            <span className="text-xs text-text-secondary">
              {run.asset.toUpperCase()} · {run.strategy}
              {' · '}
              {fmt.isoDate(run.from_date)} → {fmt.isoDate(run.to_date)}
            </span>
          )}
        </div>

        {/* Compare — disabled placeholder for F7 */}
        <button
          disabled
          title="Compare runs — coming in F7"
          className="cursor-not-allowed rounded-sm border border-border-default px-2 py-1 text-xs text-text-disabled"
        >
          Compare →
        </button>
      </div>

      {/* Tab body */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-6">
            <LoadingSkeleton variant="form" />
          </div>
        ) : (
          <div className="p-6">
            <TabsUrlSync
              tabs={[
                {
                  value: 'overview',
                  label: 'Overview',
                  content: <RunOverviewTab runId={runId} />,
                },
                {
                  value: 'signal',
                  label: 'Signal Quality',
                  content: <RunSignalQualityTab runId={runId} />,
                },
                {
                  value: 'trades',
                  label: 'Trades',
                  content: <RunTradesTab runId={runId} />,
                },
                {
                  value: 'artifacts',
                  label: 'Artifacts',
                  content: <RunArtifactsTab runId={runId} />,
                },
              ]}
              defaultTab="overview"
            />
          </div>
        )}
      </div>
    </div>
  )
}
