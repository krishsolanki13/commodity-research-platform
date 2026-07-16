import { useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRuns, useStrategies } from '@/api/hooks'
import { useComparisonBasket, MAX_COMPARISON_SIZE } from '@/stores/comparisonBasket'
import { RunTable } from '@/components/data/RunTable'
import { RunExplorerFilters } from '@/features/runs/RunExplorerFilters'
import type { SortField } from '@/features/runs/RunExplorerFilters'
import { Button } from '@/ui/button'
import { useUrlState } from '@/lib/useUrlState'
import { z } from 'zod'

const schema = z.object({
  strategy: z.string().optional(),
  asset: z.string().optional(),
  sort: z
    .enum(['sharpe', 'max_drawdown', 'total_return', 'cagr', 'executed_at'])
    .default('executed_at'),
  order: z.enum(['asc', 'desc']).default('desc'),
  q: z.string().optional(),
  page: z.coerce.number().int().min(1).default(1),
})

const defaults = {
  sort: 'executed_at' as const,
  order: 'desc' as const,
  page: 1,
}

export function RunExplorer() {
  const [{ strategy, asset, sort, order, q, page }, setUrlState] = useUrlState(schema, defaults)

  const { data, isLoading } = useRuns({
    strategy,
    asset,
    sort,
    order,
    q,
    page,
    page_size: 50,
  })
  const { data: strategiesData } = useStrategies()
  const basket = useComparisonBasket()
  const navigate = useNavigate()

  const filterKey = JSON.stringify({ strategy, asset, sort, order, q })
  const prevFilterKey = useRef(filterKey)
  useEffect(() => {
    if (prevFilterKey.current !== filterKey) {
      prevFilterKey.current = filterKey
      if (page !== 1) setUrlState({ page: 1 })
    }
    // page / setUrlState intentionally omitted — filterKey is the trigger
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey])

  function handleSelectionChange(newIds: Set<string>) {
    const added = [...newIds].filter((id) => !basket.ids.includes(id))
    const removed = basket.ids.filter((id) => !newIds.has(id))
    added.forEach((id) => basket.add(id))
    removed.forEach((id) => basket.remove(id))
  }

  const strategies = (strategiesData?.strategies ?? []).map((s) => ({
    name: s.name,
    label: s.display_name,
  }))

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="font-mono text-lg font-semibold text-text-emphasis">Run Explorer</h1>
        <span className="font-mono text-xs text-text-secondary">
          {data?.total ?? 0} runs total
        </span>
      </div>

      <div className="border-b px-6 py-3">
        <RunExplorerFilters
          strategies={strategies}
          filters={{ strategy, asset, q, sort, order }}
          onChange={(f) => setUrlState({ ...f, page: 1 })}
        />
      </div>

      <div className="flex-1 overflow-auto px-6 py-4">
        <RunTable
          rows={data?.runs ?? []}
          onRowClick={(runId) => {
            void navigate(`/runs/${runId}`)
          }}
          selection={{
            ids: new Set(basket.ids),
            onChange: handleSelectionChange,
          }}
          selectionMaxReached={basket.ids.length >= MAX_COMPARISON_SIZE}
          sortState={[{ id: sort, desc: order === 'desc' }]}
          onSort={(s) => {
            if (s.length > 0) {
              setUrlState({
                sort: s[0].id as SortField,
                order: s[0].desc ? 'desc' : 'asc',
              })
            }
          }}
          loading={isLoading}
          emptyState={{
            title: 'No runs yet',
            body: 'Evaluate a signal in the Workbench, then launch your first backtest.',
          }}
        />
      </div>

      {data && data.total > 50 && (
        <div className="flex items-center justify-end gap-2 border-t px-6 py-3">
          <span className="font-mono text-xs text-text-secondary">
            {(page - 1) * 50 + 1}–{Math.min(page * 50, data.total)} of {data.total}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setUrlState({ page: page - 1 })}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page * 50 >= data.total}
            onClick={() => setUrlState({ page: page + 1 })}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}

export default RunExplorer
