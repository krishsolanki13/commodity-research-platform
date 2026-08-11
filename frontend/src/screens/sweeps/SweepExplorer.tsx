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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/ui/select'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type ParamSpec = components['schemas']['ParamSpec']

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
  const isPolling =
    status?.status === 'queued' || status?.status === 'running'
  const { data: results } = useSweepResults(
    status?.status === 'complete' ? activeSweepId : null,
    sortBy,
    sortDir,
  )

  const selectedStrategy = useMemo(
    () =>
      (strategiesData?.strategies ?? []).find((s) => s.name === strategyName) ??
      null,
    [strategiesData, strategyName],
  )

  const sweepable = sweepableParams(selectedStrategy?.params_schema)
  const paramNames = sweepable.map((p) => p.name)
  const paramTypes = Object.fromEntries(
    sweepable.map((p) => [p.name, p.kind as 'int' | 'float']),
  ) as Record<string, 'int' | 'float'>

  const recentSweeps = (sweepList?.sweeps ?? []).slice(0, 8)
  const nCombinations =
    status?.n_combinations || launch.data?.n_combinations || undefined

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
      },
    )
  }

  function handleNewSweep() {
    setActiveSweepId(null)
  }

  if (activeSweepId !== null) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="shrink-0 px-6 pt-6 pb-4">
          <h1 className="text-xl font-semibold text-text-primary">Sweep Explorer</h1>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6">
          <div className="flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={handleNewSweep}
              className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
            >
              ← New Sweep
            </button>

            {recentSweeps.length > 0 && (
              <Select
                value={activeSweepId}
                onValueChange={(id) => setActiveSweepId(id)}
              >
                <SelectTrigger
                  className="w-[280px] font-mono text-xs"
                  aria-label="Recent sweeps"
                >
                  <SelectValue placeholder="Recent sweeps…" />
                </SelectTrigger>
                <SelectContent>
                  {recentSweeps.map((s) => (
                    <SelectItem key={s.sweep_id} value={s.sweep_id}>
                      {s.sweep_id.slice(0, 8)}… — {s.asset} / {s.strategy_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {isPolling && (
            <p className="text-center text-xs text-text-secondary">
              {status?.n_complete
                ? `Running sweep… ${status.n_complete} of ${nCombinations ?? '?'} complete`
                : `Running sweep of ${nCombinations ?? '?'} combinations…`}
            </p>
          )}

          {status?.status === 'failed' && (
            <p className="text-center text-xs text-loss">
              Sweep failed{status.error ? `: ${status.error}` : ''}
            </p>
          )}

          {status?.status === 'complete' && (
            <>
              <SweepResultsTable
                runs={results?.runs ?? []}
                sortBy={sortBy}
                sortDir={sortDir}
                onSort={handleSort}
              />
              <ParallelCoordinatesChart
                runs={results?.runs ?? []}
                paramKeys={
                  Object.keys(paramGrid).length > 0
                    ? Object.keys(paramGrid)
                    : Object.keys(results?.param_grid ?? {})
                }
              />
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 px-6 pt-6 pb-4">
        <h1 className="text-xl font-semibold text-text-primary">Sweep Explorer</h1>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
        <div className="min-h-0 overflow-y-auto">
          <Panel title="Sweep Configuration">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
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

              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                  Strategy
                </span>
                <Select
                  value={strategyName ?? undefined}
                  onValueChange={handleStrategyChange}
                >
                  <SelectTrigger
                    className="w-full font-mono text-sm"
                    aria-label="Select strategy"
                  >
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

              <div className="flex flex-col gap-1.5">
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

              <Button
                variant="primary"
                className="w-full"
                disabled={
                  !asset || !strategyName || !gridValid || launch.isPending
                }
                onClick={handleLaunch}
              >
                {launch.isPending ? 'Launching…' : 'Launch Sweep'}
              </Button>
            </div>
          </Panel>
        </div>

        <div className="min-h-0 overflow-y-auto">
          <Panel title="Results">
            <div className="flex flex-col gap-4">
              {recentSweeps.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                    Recent Sweeps
                  </span>
                  <div className="flex flex-col gap-0.5">
                    {recentSweeps.map((s) => (
                      <button
                        key={s.sweep_id}
                        type="button"
                        onClick={() => setActiveSweepId(s.sweep_id)}
                        className={cn(
                          'rounded px-2 py-1.5 text-left font-mono text-xs transition-colors',
                          'text-text-secondary hover:bg-bg-hover hover:text-text-primary',
                        )}
                      >
                        {s.sweep_id.slice(0, 8)}… — {s.asset} / {s.strategy_name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-xs text-text-secondary">
                Configure and launch a sweep, or select a recent sweep to view
                results.
              </p>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

export default SweepExplorer
