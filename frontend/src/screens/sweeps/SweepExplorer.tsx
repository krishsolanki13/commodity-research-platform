import { useMemo, useState } from 'react'
import { z } from 'zod'
import { useUrlState } from '@/lib/useUrlState'
import {
  useAssets,
  useStrategies,
  useSweepLaunch,
  useSweepStatus,
  useSweepResults,
  useSweeps,
} from '@/api/hooks'
import { useSweepHistory } from '@/stores/sweepHistory'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { SweepParamGridBuilder } from '@/features/sweeps/SweepParamGridBuilder'
import { SweepResultsTable } from '@/features/sweeps/SweepResultsTable'
import { ParallelCoordinatesChart } from '@/components/charts/ParallelCoordinatesChart'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type ParamSpec = components['schemas']['ParamSpec']
type SweepListItem = components['schemas']['SweepListItem']

const sweepSchema = z.object({
  sweep_id: z.string().optional(),
  sort_by: z.string().default('sharpe'),
  sort_dir: z.enum(['asc', 'desc']).default('desc'),
  asset: z.string().optional(),
  strategy_name: z.string().optional(),
})

const sweepDefaults = {
  sort_by: 'sharpe' as const,
  sort_dir: 'desc' as const,
}

function sweepableParams(schema: ParamSpec[] | undefined) {
  return (schema ?? []).filter((p) => p.kind === 'int' || p.kind === 'float')
}

function deriveSweepStatus(s: SweepListItem): string {
  const done = s.n_complete + s.n_failed
  if (done >= s.n_combinations) {
    return s.n_complete === 0 && s.n_failed > 0 ? 'failed' : 'complete'
  }
  return 'running'
}

export function SweepExplorer() {
  const [urlState, setUrlState] = useUrlState(sweepSchema, sweepDefaults)
  const activeSweepId = urlState.sweep_id ?? null
  const sortBy = urlState.sort_by
  const sortDir = urlState.sort_dir
  const asset = urlState.asset ?? null
  const strategyName = urlState.strategy_name ?? null

  const [paramGrid, setParamGrid] = useState<Record<string, unknown[]>>({})
  const [gridValid, setGridValid] = useState(false)

  const { data: assetsData } = useAssets()
  const { data: strategiesData } = useStrategies()
  const { data: sweepList } = useSweeps()
  const addSweep = useSweepHistory((s) => s.addSweep)

  const launch = useSweepLaunch()
  const { data: status } = useSweepStatus(activeSweepId)
  const { data: results } = useSweepResults(
    status?.status === 'complete' ? activeSweepId : null,
    sortBy,
    sortDir
  )

  const selectedStrategy = useMemo(
    () => (strategiesData?.strategies ?? []).find((s) => s.name === strategyName) ?? null,
    [strategiesData, strategyName]
  )

  const sweepable = sweepableParams(selectedStrategy?.params_schema)
  const paramNames = sweepable.map((p) => p.name)
  const paramTypes = Object.fromEntries(
    sweepable.map((p) => [p.name, p.kind as 'int' | 'float'])
  ) as Record<string, 'int' | 'float'>

  const recentSweeps = (sweepList?.sweeps ?? []).slice(0, 8)
  const nCombinations = status?.n_combinations || launch.data?.n_combinations || undefined
  const hasResults = !!(results?.runs && results.runs.length > 0)

  function setActiveSweepId(id: string | null) {
    setUrlState({ sweep_id: id })
  }

  function handleSort(col: string) {
    if (col === sortBy) {
      setUrlState({ sort_dir: sortDir === 'asc' ? 'desc' : 'asc' })
    } else {
      setUrlState({ sort_by: col, sort_dir: 'desc' })
    }
  }

  function handleStrategyChange(name: string) {
    setUrlState({ strategy_name: name })
    setParamGrid({})
    setGridValid(false)
  }

  function handleLaunch() {
    if (!asset || !strategyName || !gridValid) return
    launch.mutate(
      { asset, strategy_name: strategyName, param_grid: paramGrid },
      {
        onSuccess: (data) => {
          setActiveSweepId(data.sweep_id)
          addSweep(data.sweep_id)
        },
      }
    )
  }

  function handleNewSweep() {
    setActiveSweepId(null)
  }

  if (hasResults) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="shrink-0 px-6 pb-4 pt-6">
          <h1 className="text-xl font-semibold text-text-primary">Sweep Explorer</h1>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6">
          <button
            type="button"
            onClick={handleNewSweep}
            className="flex w-fit shrink-0 items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
          >
            ← New Sweep
          </button>

          <SweepResultsTable
            runs={results?.runs ?? []}
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={handleSort}
          />
          <div className="shrink-0">
            <ParallelCoordinatesChart
              runs={results?.runs ?? []}
              paramKeys={
                Object.keys(paramGrid).length > 0
                  ? Object.keys(paramGrid)
                  : Object.keys(results?.param_grid ?? {})
              }
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pb-4 pt-6">
        <h1 className="text-xl font-semibold text-text-primary">Sweep Explorer</h1>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
        <div className="min-h-0 overflow-y-auto">
          <Panel title="Sweep Configuration">
            <div className="flex flex-col gap-4">
              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Asset
                </span>
                <AssetSelector
                  value={asset}
                  onChange={(v) => setUrlState({ asset: v ?? null })}
                  assets={assetsData?.assets ?? []}
                  aria-label="Select commodity asset"
                />
              </div>

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Strategy
                </span>
                <Select value={strategyName ?? undefined} onValueChange={handleStrategyChange}>
                  <SelectTrigger className="w-full font-mono text-sm" aria-label="Select strategy">
                    <SelectValue placeholder="Select strategy…" />
                  </SelectTrigger>
                  <SelectContent>
                    {(strategiesData?.strategies ?? []).map((s) => (
                      <SelectItem key={s.name} value={s.name}>
                        {s.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Parameter Ranges
                </span>
                <SweepParamGridBuilder
                  paramNames={paramNames}
                  paramTypes={paramTypes}
                  onChange={(grid, valid) => {
                    setParamGrid(grid)
                    setGridValid(valid)
                  }}
                />
              </div>
            </div>
          </Panel>
        </div>

        <div className="min-h-0 overflow-y-auto">
          <Panel title="Launch">
            <div className="flex flex-col gap-4">
              <Button
                variant="primary"
                className="w-full"
                disabled={!asset || !strategyName || !gridValid || launch.isPending}
                onClick={handleLaunch}
              >
                {launch.isPending ? 'Launching…' : 'Launch Sweep'}
              </Button>

              {activeSweepId && status?.status === 'queued' && (
                <p className="mt-4 text-center text-sm text-text-secondary">Queued…</p>
              )}
              {activeSweepId && status?.status === 'running' && (
                <p className="mt-4 text-center text-sm text-text-secondary">
                  Running sweep of {nCombinations ?? '?'} combinations…
                </p>
              )}
              {activeSweepId && status?.status === 'failed' && (
                <p className="mt-4 text-center text-sm text-loss">
                  Sweep failed{status.error ? `: ${status.error}` : ''}
                </p>
              )}

              <div className="gap-1.5 flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Recent Sweeps
                </span>
                {recentSweeps.length === 0 ? (
                  <p className="text-xs text-text-secondary">
                    No previous sweeps. Configure and launch above.
                  </p>
                ) : (
                  <div className="gap-0.5 flex flex-col">
                    {recentSweeps.map((s) => {
                      const badge = deriveSweepStatus(s)
                      return (
                        <button
                          key={s.sweep_id}
                          type="button"
                          onClick={() => setActiveSweepId(s.sweep_id)}
                          className={cn(
                            'py-1.5 flex items-center justify-between gap-2 rounded px-2 text-left font-mono text-xs transition-colors',
                            activeSweepId === s.sweep_id
                              ? 'bg-bg-selected text-text-accent'
                              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                          )}
                        >
                          <span className="min-w-0 truncate">
                            {s.sweep_id.slice(0, 8)}… · {s.asset} / {s.strategy_name}
                          </span>
                          <span
                            className={cn(
                              'px-1.5 py-0.5 shrink-0 rounded-full text-[10px] font-medium',
                              badge === 'complete'
                                ? 'bg-gain-fill text-gain'
                                : badge === 'failed'
                                  ? 'bg-loss-fill text-loss'
                                  : 'bg-bg-raised text-text-secondary'
                            )}
                          >
                            {badge}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

export default SweepExplorer
