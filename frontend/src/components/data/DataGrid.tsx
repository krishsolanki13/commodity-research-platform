/**
 * DataGrid<T> — universal table engine.
 *
 * Built on TanStack Table (headless logic) + TanStack Virtual (row virtualization).
 * Generic over T — zero domain type knowledge. All column definitions and
 * formatting are the caller's responsibility.
 *
 * Features:
 *   - Client-side sort (controlled or uncontrolled), filter, column visibility
 *   - Row virtualization: auto-enabled when data.length > 200 or virtualized=true
 *   - Toolbar: global search, CSV export of filtered view, column visibility toggle
 *   - Selection: Set<string> ↔ TanStack RowSelectionState conversion
 *   - Keyboard navigation: j (down), k (up), Enter (click) — suppressed in inputs
 *   - Server pagination mode (disables client sort/filter)
 *   - Loading state: LoadingSkeleton variant="table"
 *
 * Does NOT: fetch data, import domain types, apply fmt/tone formatting.
 */
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
  type RowSelectionState,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef, useState, useEffect } from 'react'
import { ChevronUp, ChevronDown, Download, Search } from 'lucide-react'
import { cn } from '@/lib/cn'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'

// ---------------------------------------------------------------------------
// Local display types — not from API schema
// ---------------------------------------------------------------------------

export interface ServerPage {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}

// ---------------------------------------------------------------------------
// Selection helpers
// ---------------------------------------------------------------------------

function selectionToTanstack(ids?: Set<string>): RowSelectionState {
  if (!ids) return {}
  const result: RowSelectionState = {}
  ids.forEach((id) => {
    result[id] = true
  })
  return result
}

function tanstackToSelection(state: RowSelectionState): Set<string> {
  return new Set(Object.keys(state).filter((k) => state[k]))
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

function exportToCsv<T>(table: ReturnType<typeof useReactTable<T>>, filename: string) {
  const headers = table
    .getAllLeafColumns()
    .filter((col) => col.getIsVisible() && col.id !== '__select__')
    .map((col) => col.id)

  const rows = table.getFilteredRowModel().rows.map((row) =>
    headers.map((h) => {
      const v = row.getValue(h)
      let str = ''
      if (v == null) str = ''
      else if (typeof v === 'string') str = v
      else if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint')
        str = String(v)
      else str = JSON.stringify(v)
      return str.includes(',') ? `"${str}"` : str
    })
  )

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DataGridProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  getRowId: (row: T) => string
  onRowClick?: (row: T) => void
  onHoverRow?: (row: T) => void
  selection?: {
    ids: Set<string>
    onChange: (ids: Set<string>) => void
  }
  toolbar?: {
    search?: boolean
    export?: boolean
    columnVisibility?: boolean
  }
  virtualized?: boolean
  sortState?: SortingState
  onSort?: (state: SortingState) => void
  emptyState?: { title: string; body: string }
  loading?: boolean
  serverPage?: ServerPage
  rowHeight?: number
  className?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DataGrid<T>({
  columns: userColumns,
  data,
  getRowId,
  onRowClick,
  onHoverRow,
  selection,
  toolbar,
  virtualized,
  sortState,
  onSort,
  emptyState,
  loading,
  serverPage,
  rowHeight = 32,
  className,
}: DataGridProps<T>) {
  const [internalSort, setInternalSort] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [focusedIdx, setFocusedIdx] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Prepend selection column only when selection prop is provided
  const columns: ColumnDef<T>[] = selection
    ? [
        {
          id: '__select__',
          header: ({ table }) => (
            <input
              type="checkbox"
              checked={table.getIsAllRowsSelected()}
              onChange={table.getToggleAllRowsSelectedHandler()}
              aria-label="Select all rows"
              className="cursor-pointer"
            />
          ),
          cell: ({ row }) => (
            <input
              type="checkbox"
              checked={row.getIsSelected()}
              onChange={row.getToggleSelectedHandler()}
              onClick={(e) => e.stopPropagation()}
              aria-label={`Select row ${row.id}`}
              className="cursor-pointer"
            />
          ),
          size: 40,
        },
        ...userColumns,
      ]
    : userColumns

  const table = useReactTable<T>({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getRowId,
    state: {
      sorting: sortState ?? internalSort,
      globalFilter,
      columnVisibility,
      rowSelection: selectionToTanstack(selection?.ids),
    },
    onSortingChange: (updater) => {
      const next = typeof updater === 'function' ? updater(sortState ?? internalSort) : updater
      if (onSort) {
        onSort(next)
      } else {
        setInternalSort(next)
      }
    },
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: (updater) => {
      const prev = selectionToTanstack(selection?.ids)
      const next = typeof updater === 'function' ? updater(prev) : updater
      selection?.onChange(tanstackToSelection(next))
    },
    enableRowSelection: !!selection,
    // Force ascending-first on all columns (TanStack auto-infers desc-first for numbers)
    sortDescFirst: false,
    // Server page mode: disable client-side sort/filter
    manualSorting: !!serverPage,
    manualFiltering: !!serverPage,
  })

  const rows = table.getRowModel().rows
  const shouldVirtualize = virtualized ?? data.length > 200

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
    enabled: shouldVirtualize,
  })

  // Keyboard navigation: j/k/Enter — suppressed when an input is focused
  useEffect(() => {
    const container = scrollRef.current
    if (!container) return

    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      if (e.key === 'j') {
        e.preventDefault()
        setFocusedIdx((prev) => {
          const next = Math.min((prev ?? -1) + 1, rows.length - 1)
          virtualizer.scrollToIndex(next)
          return next
        })
      } else if (e.key === 'k') {
        e.preventDefault()
        setFocusedIdx((prev) => {
          const next = Math.max((prev ?? rows.length) - 1, 0)
          virtualizer.scrollToIndex(next)
          return next
        })
      } else if (e.key === 'Enter' && focusedIdx !== null) {
        const row = rows[focusedIdx]
        if (row) onRowClick?.(row.original)
      }
    }

    container.addEventListener('keydown', onKeyDown)
    return () => container.removeEventListener('keydown', onKeyDown)
  }, [rows, focusedIdx, onRowClick, virtualizer])

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (loading) {
    return <LoadingSkeleton variant="table" rows={5} className={className} />
  }

  // ---------------------------------------------------------------------------
  // Virtualizer items
  // ---------------------------------------------------------------------------

  const virtualItems = shouldVirtualize
    ? virtualizer.getVirtualItems()
    : rows.map((_, i) => ({ index: i, start: i * rowHeight, size: rowHeight }))

  const totalHeight = shouldVirtualize ? virtualizer.getTotalSize() : rows.length * rowHeight
  const totalColWidth = table.getAllLeafColumns().reduce((sum, col) => sum + col.getSize(), 0)

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={cn('flex h-full w-full flex-col', className)}>
      {/* Toolbar */}
      {toolbar && (
        <div className="flex shrink-0 items-center gap-2 border-b border-border-default px-3 py-2">
          {toolbar.search && (
            <div className="relative max-w-xs flex-1">
              <Search
                size={12}
                strokeWidth={1.75}
                className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-text-secondary"
              />
              <input
                type="text"
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                placeholder="Search..."
                className={cn(
                  'h-7 w-full rounded-sm border border-border-strong bg-bg-app pl-7 pr-3',
                  'font-mono text-xs text-text-primary placeholder:text-text-secondary',
                  'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent'
                )}
              />
            </div>
          )}

          <div className="flex-1" />

          {toolbar.export && (
            <button
              onClick={() => exportToCsv(table, `export-${Date.now()}.csv`)}
              className={cn(
                'flex items-center gap-1 rounded-sm px-2 py-1',
                'text-xs text-text-secondary hover:bg-bg-hover hover:text-text-primary',
                'transition-colors duration-fast'
              )}
            >
              <Download size={12} strokeWidth={1.75} />
              CSV
            </button>
          )}

          {serverPage && (
            <span className="font-mono text-xs text-text-secondary">
              {(serverPage.page - 1) * serverPage.pageSize + 1}–
              {Math.min(serverPage.page * serverPage.pageSize, serverPage.total)} of{' '}
              {serverPage.total.toLocaleString()}
            </span>
          )}
        </div>
      )}

      {/* Scrollable table container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto"
        tabIndex={0}
        style={{ outline: 'none' }}
      >
        <table
          role="grid"
          className="w-full border-collapse text-sm"
          style={{
            tableLayout: 'fixed',
            // Stretch to container; minWidth keeps columns readable when narrow.
            // Absolute-positioned body rows must share the same width as thead.
            width: '100%',
            minWidth: totalColWidth,
          }}
        >
          <thead className="sticky top-0 z-10 bg-bg-raised">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    style={{
                      width: `${"$"}{(header.getSize() / totalColWidth) * 100}%`,
                      minWidth: header.getSize(),
                    }}
                    className={cn(
                      'border-b border-border-default px-3 py-2 text-left',
                      'text-xs font-medium uppercase tracking-wider text-text-secondary',
                      header.column.getCanSort() &&
                        'cursor-pointer select-none hover:text-text-primary'
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                    aria-sort={
                      header.column.getIsSorted() === 'asc'
                        ? 'ascending'
                        : header.column.getIsSorted() === 'desc'
                          ? 'descending'
                          : header.column.getCanSort()
                            ? 'none'
                            : undefined
                    }
                  >
                    <div className="flex items-center gap-1">
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getIsSorted() === 'asc' && (
                        <ChevronUp size={10} strokeWidth={2} />
                      )}
                      {header.column.getIsSorted() === 'desc' && (
                        <ChevronDown size={10} strokeWidth={2} />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody
            style={{
              height: totalHeight,
              position: 'relative',
              display: 'block',
            }}
          >
            {rows.length === 0 ? (
              <tr style={{ display: 'table-row' }}>
                <td
                  colSpan={columns.length}
                  className="py-12 text-center text-sm text-text-secondary"
                >
                  {emptyState
                    ? `${emptyState.title}${emptyState.body ? `: ${emptyState.body}` : ''}`
                    : 'No data'}
                </td>
              </tr>
            ) : (
              virtualItems.map((virtualRow) => {
                const row = rows[virtualRow.index]
                if (!row) return null
                return (
                  <tr
                    key={row.id}
                    data-focused={focusedIdx === virtualRow.index ? 'true' : undefined}
                    onClick={() => onRowClick?.(row.original)}
                    onMouseEnter={onHoverRow ? () => onHoverRow(row.original) : undefined}
                    aria-selected={row.getIsSelected() || undefined}
                    className={cn(
                      'absolute left-0 top-0 w-full border-b border-border-default',
                      'transition-colors duration-fast',
                      onRowClick && 'cursor-pointer',
                      'hover:bg-bg-hover',
                      row.getIsSelected() && 'border-l-2 border-l-accent bg-bg-selected',
                      focusedIdx === virtualRow.index && 'bg-bg-hover'
                    )}
                    style={{
                      height: rowHeight,
                      transform: `translateY(${virtualRow.start}px)`,
                      display: 'table',
                      tableLayout: 'fixed',
                      width: '100%',
                      minWidth: totalColWidth,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="overflow-hidden text-ellipsis whitespace-nowrap px-3 py-0 text-text-primary"
                        style={{
                          verticalAlign: 'middle',
                          height: rowHeight,
                          width: `${"$"}{(cell.column.getSize() / totalColWidth) * 100}%`,
                          minWidth: cell.column.getSize(),
                        }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Server pagination */}
      {serverPage && (
        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-border-default px-3 py-2">
          <button
            onClick={() => serverPage.onPage(serverPage.page - 1)}
            disabled={serverPage.page <= 1}
            className={cn(
              'rounded-sm px-2 py-1 text-xs text-text-secondary',
              'hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-50'
            )}
          >
            Previous
          </button>
          <button
            onClick={() => serverPage.onPage(serverPage.page + 1)}
            disabled={serverPage.page * serverPage.pageSize >= serverPage.total}
            className={cn(
              'rounded-sm px-2 py-1 text-xs text-text-secondary',
              'hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-50'
            )}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
