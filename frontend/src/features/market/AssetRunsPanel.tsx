import { useNavigate, Link } from 'react-router-dom'
import { useRuns } from '@/api/hooks/useRuns'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { EmptyState } from '@/components/layout/EmptyState'
import { fmt } from '@/lib/fmt'
import type { components } from '@/api/schema'

type RunListItem = components['schemas']['RunListItem']

interface AssetRunsPanelProps {
  asset: string
  displayName: string
}

export function AssetRunsPanel({ asset, displayName }: AssetRunsPanelProps) {
  const navigate = useNavigate()
  const { data, isLoading } = useRuns({ asset, page: 1, page_size: 5 })
  const runs: RunListItem[] = data?.runs ?? []

  if (!isLoading && runs.length === 0) {
    return (
      <EmptyState
        title={`No runs for ${displayName} yet`}
        body="Run a backtest from the Strategy Builder to see results here."
        action={{ label: 'Open Strategy Builder', href: '/backtest/new' }}
      />
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-auto rounded-md border border-border-default">
        {isLoading ? (
          <div className="flex h-24 items-center justify-center text-xs text-text-secondary">
            Loading…
          </div>
        ) : (
          <table
            role="grid"
            aria-label="Asset runs"
            className="w-full table-fixed border-collapse text-sm"
          >
            <thead className="bg-bg-raised">
              <tr>
                {(['STATUS', 'RUN ID', 'SHARPE', 'MAX DD', 'EXECUTED'] as const).map((heading) => (
                  <th
                    key={heading}
                    scope="col"
                    className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((row) => (
                <tr
                  key={row.run_id}
                  className="cursor-pointer border-b border-border-default transition-colors hover:bg-bg-hover"
                  onClick={() => void navigate(`/runs/${row.run_id}`)}
                >
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <RunStatusBadge status={row.status} />
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span
                      className="block max-w-[160px] truncate font-mono text-xs"
                      title={row.run_id}
                    >
                      {row.run_id.slice(-20)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    {row.sharpe != null ? (
                      <span className="font-mono text-xs">{fmt.ratio(row.sharpe)}</span>
                    ) : (
                      <span className="text-text-secondary">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    {row.max_drawdown != null ? (
                      <span className="font-mono text-xs">{fmt.drawdown(row.max_drawdown)}</span>
                    ) : (
                      <span className="text-text-secondary">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span className="font-mono text-xs text-text-secondary">
                      {fmt.isoDate(row.executed_at)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="text-right">
        <Link
          to={`/runs?asset=${asset}`}
          className="text-xs text-text-accent hover:text-accent-hover"
        >
          → All runs for {displayName}
        </Link>
      </div>
    </div>
  )
}
