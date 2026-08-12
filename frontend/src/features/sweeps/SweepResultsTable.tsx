// Reference: src/components/data/PortfolioAssetTable.tsx — TDR-011 plain HTML table
// Sort state controlled via props from SweepExplorer URL state

import type { components } from '@/api/schema'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { dec, pct } from '@/lib/fmt'

type SweepRunSummaryResponse = components['schemas']['SweepRunSummaryResponse']
type RunStatus = 'queued' | 'running' | 'complete' | 'failed'

interface SweepResultsTableProps {
  runs: SweepRunSummaryResponse[]
  sortBy: string
  sortDir: 'asc' | 'desc'
  onSort: (col: string) => void
}

function SortIndicator({ active, dir }: { active: boolean; dir: string }) {
  if (!active)
    return <span className="ml-1 text-text-secondary opacity-40">↕</span>
  return (
    <span className="ml-1 text-text-accent">{dir === 'asc' ? '↑' : '↓'}</span>
  )
}

function formatParams(params: Record<string, unknown>): string {
  return Object.entries(params)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

function toRunStatus(status: string): RunStatus {
  if (
    status === 'queued' ||
    status === 'running' ||
    status === 'complete' ||
    status === 'failed'
  ) {
    return status
  }
  return 'running'
}

const SORTABLE_COLS: { key: string; label: string }[] = [
  { key: 'sharpe', label: 'SHARPE' },
  { key: 'max_drawdown', label: 'MAX DD' },
  { key: 'total_return', label: 'RETURN' },
]

export function SweepResultsTable({
  runs,
  sortBy,
  sortDir,
  onSort,
}: SweepResultsTableProps) {
  if (runs.length === 0) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-8 text-center">
        <p className="text-sm text-text-secondary">No sweep results yet.</p>
      </div>
    )
  }

  const maxSharpe = Math.max(...runs.map((r) => r.sharpe ?? -Infinity))

  return (
    <div className="shrink-0 rounded border border-border-default">
      <table className="w-full table-fixed border-collapse text-sm">
        <colgroup>
          <col className="w-[38%]" />
          <col className="w-[12%]" />
          <col className="w-[12%]" />
          <col className="w-[12%]" />
          <col className="w-[12%]" />
          <col className="w-[14%]" />
        </colgroup>
        <thead className="bg-bg-raised">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
              Params
            </th>
            {SORTABLE_COLS.map((col) => (
              <th
                key={col.key}
                className="cursor-pointer px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary hover:text-text-primary"
                onClick={() => onSort(col.key)}
              >
                {col.label}
                <SortIndicator active={sortBy === col.key} dir={sortDir} />
              </th>
            ))}
            <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary">
              Trades
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-default">
          {runs.map((run, i) => {
            const isBest =
              run.sharpe != null && run.sharpe === maxSharpe
            return (
              <tr
                key={i}
                className={isBest ? 'bg-bg-selected' : 'hover:bg-bg-hover'}
              >
                <td className="truncate px-3 py-2 font-mono text-xs text-text-secondary">
                  {formatParams(
                    (run.parameters as Record<string, unknown>) ?? {},
                  )}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {run.sharpe != null ? dec(run.sharpe, 2) : '—'}
                </td>
                <td className="px-3 py-2 text-right font-mono text-loss">
                  {run.max_drawdown != null ? pct(run.max_drawdown, 1) : '—'}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {run.total_return != null ? pct(run.total_return, 1) : '—'}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-secondary">
                  {run.n_trades ?? '—'}
                </td>
                <td className="px-3 py-2 text-right">
                  <span className="inline-flex justify-end">
                    <RunStatusBadge status={toRunStatus(run.status)} />
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
