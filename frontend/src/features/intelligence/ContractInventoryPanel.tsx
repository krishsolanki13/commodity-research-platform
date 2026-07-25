import { AlertTriangle } from 'lucide-react'
import type { components } from '@/api/schema'
import { fmt } from '@/lib/fmt'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']
type CurvePointResponse = components['schemas']['CurvePointResponse']

export interface ContractInventoryPanelProps {
  snapshot: FuturesCurveResponse | null
  loading?: boolean
}

export function ContractInventoryPanel({ snapshot, loading }: ContractInventoryPanelProps) {
  const asset = snapshot?.asset ?? ''
  const points: CurvePointResponse[] = snapshot?.points ?? []

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
        className="w-full overflow-auto rounded-md border border-border-default"
        style={{ height: 220 }}
      >
        {loading ? (
          <div className="flex h-full items-center justify-center text-xs text-text-secondary">
            Loading…
          </div>
        ) : points.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-text-secondary">
            No contract settlement data for this asset.
          </div>
        ) : (
          <table
            role="grid"
            aria-label="Contract inventory"
            className="w-full table-fixed border-collapse text-sm"
          >
            <thead className="bg-bg-raised">
              <tr>
                {(['TICKER', 'SETTLE', 'DTD', 'DATA DATE'] as const).map((heading) => (
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
              {points.map((row) => (
                <tr
                  key={row.ticker}
                  className="border-b border-border-default transition-colors hover:bg-bg-hover"
                >
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span className="font-mono text-xs font-medium">{row.ticker}</span>
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span className="font-mono text-xs">{fmt.price(row.close, asset)}</span>
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span className="font-mono text-xs text-text-secondary">
                      {row.days_to_delivery}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-sm text-text-primary">
                    <span className="font-mono text-xs text-text-secondary">
                      {fmt.isoDate(row.data_date)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
