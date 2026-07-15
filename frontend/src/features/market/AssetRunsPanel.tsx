import { useNavigate, Link } from 'react-router-dom'
import { useRuns } from '@/api/hooks/useRuns'
import { DataGrid } from '@/components/data/DataGrid'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { EmptyState } from '@/components/layout/EmptyState'
import { fmt } from '@/lib/fmt'
import { createColumnHelper } from '@tanstack/react-table'
import type { components } from '@/api/schema'

type RunListItem = components['schemas']['RunListItem']

const colHelper = createColumnHelper<RunListItem>()

const columns = [
  colHelper.accessor('status', {
    header: 'STATUS',
    enableSorting: false,
    cell: (info) => <RunStatusBadge status={info.getValue()} />,
  }),
  colHelper.accessor('run_id', {
    header: 'RUN ID',
    enableSorting: false,
    cell: (info) => (
      <span className="block max-w-[160px] truncate font-mono text-xs" title={info.getValue()}>
        {info.getValue().slice(-20)}
      </span>
    ),
  }),
  colHelper.accessor('sharpe', {
    header: 'SHARPE',
    cell: (info) => {
      const v = info.getValue()
      return v != null ? (
        <span className="font-mono text-xs">{fmt.ratio(v)}</span>
      ) : (
        <span className="text-text-secondary">—</span>
      )
    },
  }),
  colHelper.accessor('max_drawdown', {
    header: 'MAX DD',
    cell: (info) => {
      const v = info.getValue()
      return v != null ? (
        <span className="font-mono text-xs">{fmt.drawdown(v)}</span>
      ) : (
        <span className="text-text-secondary">—</span>
      )
    },
  }),
  colHelper.accessor('executed_at', {
    header: 'EXECUTED',
    cell: (info) => (
      <span className="font-mono text-xs text-text-secondary">{fmt.isoDate(info.getValue())}</span>
    ),
  }),
]

interface AssetRunsPanelProps {
  asset: string
  displayName: string
}

export function AssetRunsPanel({ asset, displayName }: AssetRunsPanelProps) {
  const navigate = useNavigate()
  const { data, isLoading } = useRuns({ asset, page: 1, page_size: 5 })
  const runs = data?.runs ?? []

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
      <DataGrid<RunListItem>
        columns={columns}
        data={runs}
        getRowId={(r) => r.run_id}
        onRowClick={(r) => {
          void navigate(`/runs/${r.run_id}`)
        }}
        loading={isLoading}
        toolbar={{ search: false, export: false }}
      />
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
