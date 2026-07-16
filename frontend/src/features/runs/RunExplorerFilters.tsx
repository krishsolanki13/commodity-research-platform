import { useState, useEffect } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/ui/select'
import { cn } from '@/lib/cn'

export type SortField =
  | 'sharpe'
  | 'max_drawdown'
  | 'total_return'
  | 'cagr'
  | 'executed_at'

export interface RunExplorerFilterValues {
  strategy?: string
  asset?: string
  q?: string
  sort: SortField
  order: 'asc' | 'desc'
}

interface RunExplorerFiltersProps {
  strategies: { name: string; label: string }[]
  filters: RunExplorerFilterValues
  onChange: (filters: RunExplorerFilterValues) => void
  className?: string
}

const SORT_OPTIONS: { value: SortField; label: string }[] = [
  { value: 'executed_at', label: 'Executed' },
  { value: 'sharpe', label: 'Sharpe' },
  { value: 'total_return', label: 'Return' },
  { value: 'max_drawdown', label: 'Max DD' },
  { value: 'cagr', label: 'CAGR' },
]

const ASSET_NAMES = ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas']

/** Radix Select disallows empty-string item values. */
const ALL_VALUE = '__all__'

export function RunExplorerFilters({
  strategies,
  filters,
  onChange,
  className,
}: RunExplorerFiltersProps) {
  const [localQ, setLocalQ] = useState(filters.q ?? '')

  useEffect(() => {
    const timer = setTimeout(() => {
      if (localQ !== (filters.q ?? '')) {
        onChange({ ...filters, q: localQ || undefined })
      }
    }, 300)
    return () => clearTimeout(timer)
    // filters and onChange intentionally omitted — localQ is the only trigger
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [localQ])

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <Select
        value={filters.strategy ?? ALL_VALUE}
        onValueChange={(value) =>
          onChange({ ...filters, strategy: value === ALL_VALUE ? undefined : value })
        }
      >
        <SelectTrigger className="h-8 w-[160px] font-mono text-xs" aria-label="Strategy filter">
          <SelectValue placeholder="All strategies" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All strategies</SelectItem>
          {strategies.map((s) => (
            <SelectItem key={s.name} value={s.name}>
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.asset ?? ALL_VALUE}
        onValueChange={(value) =>
          onChange({ ...filters, asset: value === ALL_VALUE ? undefined : value })
        }
      >
        <SelectTrigger className="h-8 w-[140px] font-mono text-xs" aria-label="Asset filter">
          <SelectValue placeholder="All assets" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_VALUE}>All assets</SelectItem>
          {ASSET_NAMES.map((name) => (
            <SelectItem key={name} value={name}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <input
        type="search"
        value={localQ}
        onChange={(e) => setLocalQ(e.target.value)}
        placeholder="Search runs…"
        aria-label="Search runs"
        className={cn(
          'h-8 w-[180px] rounded-md border border-border-strong bg-bg-app px-3',
          'font-mono text-xs text-text-primary placeholder:text-text-secondary',
          'focus:outline-none focus:ring-2 focus:ring-accent'
        )}
      />

      <Select
        value={filters.sort}
        onValueChange={(value) => onChange({ ...filters, sort: value as SortField })}
      >
        <SelectTrigger className="h-8 w-[130px] font-mono text-xs" aria-label="Sort by">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <button
        type="button"
        aria-label={filters.order === 'asc' ? 'Sort ascending' : 'Sort descending'}
        onClick={() =>
          onChange({ ...filters, order: filters.order === 'asc' ? 'desc' : 'asc' })
        }
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-md border border-border-strong',
          'font-mono text-xs text-text-primary transition-colors',
          'hover:bg-bg-hover'
        )}
      >
        {filters.order === 'asc' ? '▲' : '▼'}
      </button>
    </div>
  )
}
