import { AlertTriangle } from 'lucide-react'
import { createColumnHelper } from '@tanstack/react-table'
import type { components } from '@/api/schema'
import { DataGrid } from '@/components/data/DataGrid'
import { fmt } from '@/lib/fmt'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']
type CurvePointResponse = components['schemas']['CurvePointResponse']

export interface ContractInventoryPanelProps {
  snapshot: FuturesCurveResponse | null
  loading?: boolean
}

const colHelper = createColumnHelper<CurvePointResponse>()

function buildColumns(asset: string) {
  return [
    colHelper.accessor('ticker', {
      header: 'TICKER',
      enableSorting: false,
      size: 90,
      cell: (info) => <span className="font-mono text-xs font-medium">{info.getValue()}</span>,
    }),
    colHelper.accessor('close', {
      header: 'SETTLE',
      enableSorting: false,
      size: 90,
      cell: (info) => (
        <span className="font-mono text-xs">{fmt.price(info.getValue(), asset)}</span>
      ),
    }),
    colHelper.accessor('days_to_delivery', {
      header: 'DTD',
      enableSorting: false,
      size: 80,
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">{info.getValue()}</span>
      ),
    }),
    colHelper.accessor('data_date', {
      header: 'DATA DATE',
      enableSorting: false,
      size: 120,
      cell: (info) => (
        <span className="font-mono text-xs text-text-secondary">
          {fmt.isoDate(info.getValue())}
        </span>
      ),
    }),
  ]
}

export function ContractInventoryPanel({ snapshot, loading }: ContractInventoryPanelProps) {
  const asset = snapshot?.asset ?? ''
  const points = snapshot?.points ?? []
  const columns = buildColumns(asset)

  return (
    <div className="bg-bg-surface flex flex-col gap-3 rounded-lg border border-border-strong p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        Contract Inventory
      </span>

      {snapshot != null && snapshot.n_contracts < 4 && (
        <div
          role="status"
          className="border-warn/30 flex items-center gap-2 rounded border bg-accent-fill px-3 py-2 text-xs text-warn"
        >
          <AlertTriangle size={14} strokeWidth={1.75} className="shrink-0" />
          <span>
            Limited contract coverage ({snapshot.n_contracts} loaded). Slope and roll-yield
            analytics require at least 4 contracts.
          </span>
        </div>
      )}

      <div
        className="overflow-hidden rounded-md border border-border-default"
        style={{ height: 220 }}
      >
        <DataGrid<CurvePointResponse>
          columns={columns}
          data={points}
          getRowId={(row) => row.ticker}
          virtualized={false}
          toolbar={false as never}
          loading={loading}
          emptyState={{
            title: 'No contracts',
            body: 'No contract settlement data for this asset.',
          }}
        />
      </div>
    </div>
  )
}
