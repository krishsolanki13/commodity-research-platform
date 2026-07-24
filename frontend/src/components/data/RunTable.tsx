import type { components } from '@/api/schema'
import type { SortingState } from '@tanstack/react-table'
import { createColumnHelper } from '@tanstack/react-table'
import { MoreHorizontal, Trash2 } from 'lucide-react'
import { DataGrid } from '@/components/data/DataGrid'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { ICBandBadge } from '@/components/data/ICBandBadge'
import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/ui/dropdown-menu'

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
  onDeleteRequest?: (runId: string) => void
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
  onDeleteRequest,
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
    colHelper.accessor('run_id', {
      header: 'RUN',
      enableSorting: false,
      size: 220,
      cell: (info) => (
        <span className="font-mono text-xs text-text-emphasis" title={info.getValue()}>
          {info.getValue()}
        </span>
      ),
    }),
    colHelper.accessor('status', {
      header: 'STATUS',
      enableSorting: false,
      size: 100,
      cell: (info) => (
        <div className="flex justify-center">
          <RunStatusBadge status={info.getValue()} />
        </div>
      ),
    }),
    colHelper.accessor('asset', {
      header: 'ASSET',
      enableSorting: false,
      size: 120,
      cell: (info) => (
        <span className="font-mono uppercase text-text-emphasis">{info.getValue()}</span>
      ),
    }),
    colHelper.accessor('strategy', {
      header: 'STRATEGY',
      enableSorting: false,
      size: 150,
      cell: (info) => <span className="text-sm">{info.getValue()}</span>,
    }),
    colHelper.accessor('sharpe', {
      header: 'SHARPE',
      size: 90,
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
      size: 90,
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
      size: 90,
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
      size: 90,
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
      size: 110,
      cell: (info) => {
        const v = info.getValue()
        if (v === null) return <span className="text-text-secondary">—</span>
        return <ICBandBadge ic={v} />
      },
    }),
    colHelper.accessor('n_trades', {
      header: 'TRADES',
      enableSorting: false,
      size: 80,
      cell: (info) => {
        const v = info.getValue()
        return <span className="font-mono">{v === null ? '—' : Math.round(v).toString()}</span>
      },
    }),
    colHelper.accessor('from_date', {
      header: 'FROM',
      enableSorting: false,
      size: 110,
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">
          {fmt.isoDate(info.getValue())}
        </span>
      ),
    }),
    colHelper.accessor('executed_at', {
      header: 'EXECUTED',
      size: 120,
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">
          {fmt.isoDate(info.getValue())}
        </span>
      ),
    }),
    colHelper.display({
      id: 'actions',
      header: '',
      enableSorting: false,
      size: 40,
      cell: ({ row }) =>
        onDeleteRequest ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="rounded-sm p-1 text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                aria-label="Run actions"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal size={14} strokeWidth={1.75} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="left" sideOffset={4} onClick={(e) => e.stopPropagation()}>
              <DropdownMenuItem
                className="cursor-pointer"
                style={{ color: 'var(--text-loss)' }}
                onClick={() => onDeleteRequest(row.original.run_id)}
              >
                <Trash2 size={12} strokeWidth={1.75} className="mr-2" />
                Delete run
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null,
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
