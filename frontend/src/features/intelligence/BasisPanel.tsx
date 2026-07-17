import type { components } from '@/api/schema'
import { Skeleton } from '@/ui/skeleton'
import { fmt } from '@/lib/fmt'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']

export interface BasisPanelProps {
  snapshot: FuturesCurveResponse | null
  loading?: boolean
}

interface BasisStatProps {
  label: string
  value: string
}

function BasisStat({ label, value }: BasisStatProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        {label}
      </span>
      <span className="font-mono text-sm text-text-primary">{value}</span>
    </div>
  )
}

export function BasisPanel({ snapshot, loading }: BasisPanelProps) {
  return (
    <div className="bg-bg-surface flex flex-col gap-4 rounded-lg border border-border-strong p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        Continuous-Contract Basis (pseudo)
      </span>

      {loading ? (
        <div className="flex gap-8">
          <Skeleton className="w-24 animate-shimmer h-10" />
          <Skeleton className="w-24 animate-shimmer h-10" />
        </div>
      ) : (
        <div className="flex gap-8">
          <BasisStat
            label="Basis"
            value={snapshot?.basis != null ? fmt.price(snapshot.basis, snapshot.asset) : '—'}
          />
          <BasisStat
            label="Basis %"
            value={snapshot?.basis_pct != null ? `${(snapshot.basis_pct * 100).toFixed(2)}%` : '—'}
          />
        </div>
      )}

      <p className="text-xs text-text-secondary">
        Basis = continuous close − front contract price. Not true cash-futures basis. Per ADR-001:
        this is a continuous-contract pseudo-basis.
      </p>
    </div>
  )
}
