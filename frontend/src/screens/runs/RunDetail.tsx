import { useParams, Link, Navigate, useNavigate } from 'react-router-dom'
import { Suspense, lazy, useState } from 'react'
import { Trash2, ClipboardCopy, Check } from 'lucide-react'
import { TabsUrlSync } from '@/ui/TabsUrlSync'
import { useRunDetail, useRunDelete } from '@/api/hooks'
import { ApiClientError } from '@/api/client'
import { useComparisonBasket } from '@/stores/comparisonBasket'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { RunOverviewTab } from '@/features/runs/RunOverviewTab'
import { RunSignalQualityTab } from '@/features/runs/RunSignalQualityTab'
import { RunTradesTab } from '@/features/runs/RunTradesTab'
import { RunArtifactsTab } from '@/features/runs/RunArtifactsTab'
import { fmt } from '@/lib/fmt'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/alert-dialog'

const RunValidationTab = lazy(() =>
  import('@/features/runs/RunValidationTab').then((m) => ({
    default: m.RunValidationTab,
  }))
)

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading, error } = useRunDetail(runId ?? '')
  const cleanRunId = (runId ?? '').replace(/^poll_/, '')
  const basket = useComparisonBasket()
  const deleteRun = useRunDelete()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [copied, setCopied] = useState(false)

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
          ← Run Explorer
        </Link>
      </div>
    )
  }

  function handleAddToCompare() {
    if (!runId) return
    if (!basket.has(runId)) {
      basket.add(runId)
    }
    void navigate('/runs/compare')
  }

  function handleConfirmDelete() {
    if (!runId) return
    deleteRun.mutate(runId, {
      onSuccess: () => {
        basket.remove(runId)
        setShowDeleteDialog(false)
        void navigate('/runs')
      },
      onError: () => setShowDeleteDialog(false),
    })
  }

  function handleCopy() {
    void navigator.clipboard.writeText(cleanRunId)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header — Q1 layout */}
      <div className="flex shrink-0 flex-col gap-2 border-b border-border-default px-6 py-3">
        {/* LINE 1: back + actions */}
        <div className="flex items-center justify-between">
          <Link
            to="/runs"
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
          >
            ← Run Explorer
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowDeleteDialog(true)}
              disabled={deleteRun.isPending}
              className="text-text-secondary transition-colors hover:text-text-loss"
              title="Delete run"
              aria-label="Delete run"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={handleAddToCompare}
              className="rounded-sm border border-border-default px-2 py-1 text-xs text-text-accent transition-colors hover:bg-bg-hover"
            >
              Compare →
            </button>
          </div>
        </div>

        {/* LINE 2: status + primary description */}
        {run && (
          <div className="flex items-center gap-3">
            <RunStatusBadge status={run.status} />
            <span className="text-sm text-text-primary">
              {run.asset.toUpperCase()} · {run.strategy}
              {' · '}
              {fmt.isoDate(run.from_date)} → {fmt.isoDate(run.to_date)}
            </span>
          </div>
        )}

        {/* LINE 3: clean run ID + clipboard */}
        <div className="gap-1.5 flex items-center">
          <span className="font-mono text-xs text-text-secondary" title={cleanRunId}>
            {cleanRunId}
          </span>
          <button
            type="button"
            onClick={handleCopy}
            className="ml-2 text-text-secondary transition-colors hover:text-text-primary"
            aria-label={copied ? 'Copied' : 'Copy run ID'}
            title={copied ? 'Copied' : 'Copy run ID'}
          >
            {copied ? <Check size={12} /> : <ClipboardCopy size={12} />}
          </button>
        </div>
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
                  value: 'validation',
                  label: 'Validation',
                  content: (
                    <Suspense fallback={<LoadingSkeleton variant="form" />}>
                      <RunValidationTab
                        asset={run?.asset ?? null}
                        strategyName={run?.strategy ?? null}
                        parameters={
                          (run?.params as { parameters?: Record<string, unknown> } | undefined)
                            ?.parameters ?? null
                        }
                      />
                    </Suspense>
                  ),
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

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete run?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{' '}
              <span className="font-mono text-text-emphasis">{cleanRunId}</span> and all its
              artifacts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              style={{ backgroundColor: 'var(--loss-500)', color: 'white' }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
