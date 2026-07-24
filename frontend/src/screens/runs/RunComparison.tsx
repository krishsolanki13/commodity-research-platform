import { useSearchParams, useNavigate, Navigate, Link } from 'react-router-dom'
import { X, AlertTriangle } from 'lucide-react'
import { useRunCompare } from '@/api/hooks'
import { AlignedCurvesChart } from '@/components/charts/AlignedCurvesChart'
import { MetricDeltaTable } from '@/components/data/MetricDeltaTable'
import { EmptyState } from '@/components/layout/EmptyState'
import { Panel } from '@/ui/Panel'
import { ErrorState } from '@/components/layout/ErrorState'
import { fmt } from '@/lib/fmt'
import type { components } from '@/api/schema'

type CompareRunSummary = components['schemas']['CompareRunSummary']

export function buildLabel(run: Pick<CompareRunSummary, 'asset' | 'strategy'>): string {
  return `${run.asset.toUpperCase()} · ${run.strategy}`
}

export function RunComparison() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const raw = searchParams.get('ids')
  const ids = raw ? raw.split(',').filter(Boolean) : []

  // Always call before redirects — enabled: ids.length >= 2 inside the hook.
  // (Calling after early returns would violate Rules of Hooks when chip removal
  // shrinks the basket from ≥2 to 1.)
  const { data, isLoading, error } = useRunCompare(ids)

  if (ids.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-center justify-between">
          <h1 className="font-mono text-lg font-semibold text-text-emphasis">Run Comparison</h1>
          <Link to="/runs" className="font-mono text-xs text-text-accent hover:text-accent-hover">
            ← Run Explorer
          </Link>
        </div>
        <EmptyState
          title="No runs selected"
          body="Add at least two runs from the Run Explorer comparison tray to compare them side by side."
          action={{ label: 'Open Run Explorer →', href: '/runs' }}
        />
      </div>
    )
  }
  if (ids.length === 1) {
    return <Navigate to={`/runs/${ids[0]}`} replace />
  }

  function removeId(idToRemove: string) {
    const newIds = ids.filter((id) => id !== idToRemove)
    if (newIds.length === 0) {
      void navigate('/runs')
      return
    }
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('ids', newIds.join(','))
        return next
      },
      { replace: true }
    )
  }

  const alignedSeriesWithLabels =
    data?.aligned_series.map((s) => {
      const runMeta = data.runs.find((r) => r.run_id === s.run_id)
      return {
        runId: s.run_id,
        label: runMeta ? buildLabel(runMeta) : s.run_id.slice(-16),
        equityNormalized: s.equity_normalized,
      }
    }) ?? []

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-mono text-lg font-semibold text-text-emphasis">Run Comparison</h1>
        <Link to="/runs" className="font-mono text-xs text-text-accent hover:text-accent-hover">
          ← Run Explorer
        </Link>
      </div>

      {/* Run chips — removable */}
      <div className="flex flex-wrap gap-2">
        {ids.map((id) => (
          <div
            key={id}
            className="flex items-center gap-1 rounded-full border border-border-strong bg-bg-raised px-3 py-1 font-mono text-xs"
          >
            {id.slice(-16)}
            <button
              onClick={() => removeId(id)}
              aria-label="Remove from comparison"
              className="ml-1 text-text-secondary hover:text-text-primary"
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>

      {/* Mixed assets notice */}
      {data?.mixed_assets && (
        <div className="flex items-center gap-3 rounded-sm border-l-[3px] border-warn bg-bg-raised px-4 py-2">
          <AlertTriangle size={14} strokeWidth={1.75} className="shrink-0 text-warn" />
          <span className="text-xs text-text-primary">
            Comparing across different assets — returns reflect both signal and commodity price
            differences.
          </span>
        </div>
      )}

      {/* Intersection info */}
      {data?.intersection_bars != null && (
        <p className="font-mono text-xs text-text-secondary">
          Aligned on {data.intersection_bars} bars · {fmt.isoDate(data.intersection_from ?? '')} →{' '}
          {fmt.isoDate(data.intersection_to ?? '')}
        </p>
      )}

      {/* Aligned equity chart — mixedAssets=false: notice is owned by the screen (A5) */}
      <AlignedCurvesChart
        series={alignedSeriesWithLabels}
        intersectionFrom={data?.intersection_from}
        intersectionTo={data?.intersection_to}
        mixedAssets={false}
        title="Normalized Returns"
        height={320}
        loading={isLoading}
        error={error ?? null}
      />

      {/* Metric delta table */}
      {data && (
        <Panel title="Metric Comparison">
          <MetricDeltaTable runs={data.runs} baseRunId={data.runs[0]?.run_id} />
        </Panel>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <ErrorState
          error={{
            message: 'One or more runs may not exist or have been deleted.',
          }}
        />
      )}
    </div>
  )
}

export default RunComparison
