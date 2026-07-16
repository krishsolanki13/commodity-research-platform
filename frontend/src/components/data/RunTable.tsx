import type { components } from '@/api/schema'
import type { SortingState } from '@tanstack/react-table'
import { createColumnHelper } from '@tanstack/react-table'
import { DataGrid } from '@/components/data/DataGrid'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { ICBandBadge } from '@/components/data/ICBandBadge'
import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'

type RunListItem = components['schemas']['RunListItem']

interface RunTableProps {
  rows: RunListItem[]
  onRowClick: (runId: string) => void
  selection: { ids: Set<string>; onChange: (ids: Set<string>) => void }
  selectionMaxReached?: boolean
  loading?: boolean
  sortState?: SortingState
  onSort?: (state: SortingState) => void
  emptyState?: { title: string; body: string }
  className?: string
}

const colHelper = createColumnHelper<RunListItem>()

function sharpeTone(v: number | null): string {
  if (v === null) return 'var(--text-secondary)'
  if (v >= 0.5) return 'var(--text-gain)'
  if (v < 0) return 'var(--text-loss)'
  return 'var(--text-primary)'
}

function signTone(v: number | null): string {
  if (v === null) return 'var(--text-secondary)'
  if (v > 0) return 'var(--text-gain)'
  if (v < 0) return 'var(--text-loss)'
  return 'var(--text-primary)'
}

export function RunTable({
  rows,
  onRowClick,
  selection,
  selectionMaxReached,
  loading,
  sortState,
  onSort,
  emptyState,
  className,
}: RunTableProps) {
  const selectionCol = colHelper.display({
    id: '__select__',
    header: ({ table }) => (
      <input
        type="checkbox"
        checked={table.getIsAllRowsSelected()}
        onChange={table.getToggleAllRowsSelectedHandler()}
        aria-label="Select all rows"
      />
    ),
    cell: ({ row }) => {
      const isSelected = selection.ids.has(row.original.run_id)
      const isDisabled = (selectionMaxReached ?? false) && !isSelected
      return (
        <input
          type="checkbox"
          checked={isSelected}
          disabled={isDisabled}
          title={isDisabled ? 'Maximum 8 runs selected for comparison' : undefined}
          aria-label={`Select run ${row.original.run_id}`}
          onClick={(e) => e.stopPropagation()}
          onChange={() => {
            const next = new Set(selection.ids)
            if (isSelected) {
              next.delete(row.original.run_id)
            } else {
              next.add(row.original.run_id)
            }
            selection.onChange(next)
          }}
        />
      )
    },
    size: 40,
  })

  const columns = [
    selectionCol,
    colHelper.accessor('status', {
      header: 'STATUS',
      enableSorting: false,
      cell: (info) => (
        <div className="flex justify-center">
          <RunStatusBadge status={info.getValue()} />
        </div>
      ),
    }),
    colHelper.accessor('asset', {
      header: 'ASSET',
      enableSorting: false,
      cell: (info) => (
        <span className="font-mono uppercase text-text-emphasis">{info.getValue()}</span>
      ),
    }),
    colHelper.accessor('strategy', {
      header: 'STRATEGY',
      enableSorting: false,
      cell: (info) => <span className="text-sm">{info.getValue()}</span>,
    }),
    colHelper.accessor('sharpe', {
      header: 'SHARPE',
      cell: (info) => {
        const v = info.getValue()
        return (
          <span className="block text-right font-mono" style={{ color: sharpeTone(v) }}>
            {v === null ? '—' : fmt.ratio(v)}
          </span>
        )
      },
    }),
    colHelper.accessor('max_drawdown', {
      header: 'MAX DD',
      cell: (info) => {
        const v = info.getValue()
        return (
          <span className="block text-right font-mono" style={{ color: 'var(--text-loss)' }}>
            {v === null ? '—' : fmt.drawdown(v)}
          </span>
        )
      },
    }),
    colHelper.accessor('total_return', {
      header: 'RETURN',
      cell: (info) => {
        const v = info.getValue()
        return (
          <span className="block text-right font-mono" style={{ color: signTone(v) }}>
            {v === null ? '—' : fmt.percent(v)}
          </span>
        )
      },
    }),
    colHelper.accessor('cagr', {
      header: 'CAGR',
      cell: (info) => {
        const v = info.getValue()
        return (
          <span className="block text-right font-mono" style={{ color: signTone(v) }}>
            {v === null ? '—' : fmt.percent(v)}
          </span>
        )
      },
    }),
    colHelper.accessor('ic', {
      header: 'IC',
      enableSorting: false,
      cell: (info) => {
        const v = info.getValue()
        if (v === null) return <span className="text-text-secondary">—</span>
        return <ICBandBadge ic={v} />
      },
    }),
    colHelper.accessor('n_trades', {
      header: 'TRADES',
      enableSorting: false,
      cell: (info) => {
        const v = info.getValue()
        return <span className="font-mono">{v === null ? '—' : Math.round(v).toString()}</span>
      },
    }),
    colHelper.accessor('from_date', {
      header: 'FROM',
      enableSorting: false,
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">
          {fmt.isoDate(info.getValue())}
        </span>
      ),
    }),
    colHelper.accessor('executed_at', {
      header: 'EXECUTED',
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">
          {fmt.isoDate(info.getValue())}
        </span>
      ),
    }),
  ]

  return (
    <DataGrid<RunListItem>
      columns={columns}
      data={rows}
      getRowId={(r) => r.run_id}
      onRowClick={(row) => onRowClick(row.run_id)}
      loading={loading}
      sortState={sortState}
      onSort={onSort}
      emptyState={emptyState}
      toolbar={false as never}
      className={cn(className)}
    />
  )
}
