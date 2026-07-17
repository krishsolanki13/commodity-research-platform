import type { ReactNode } from 'react'
import type { components } from '@/api/schema'
import { RegimeBadge } from '@/components/data/RegimeBadge'
import { Skeleton } from '@/ui/skeleton'
import { fmt } from '@/lib/fmt'
import type { Regime } from '@/lib/tone'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']

function asRegime(value: string | null | undefined): Regime | null {
  if (value === 'contango' || value === 'backwardation' || value === 'flat') return value
  return null
}

export interface CurveKPIRowProps {
  snapshot: FuturesCurveResponse | null
  loading?: boolean
}

function regimeTone(slope: number | null): string {
  if (slope == null) return 'neutral'
  if (slope > 0) return 'warn' // contango — roll cost for longs
  if (slope < 0) return 'gain' // backwardation — roll yield for longs
  return 'neutral'
}

function rollTone(rollYield: number | null): string {
  if (rollYield == null) return 'neutral'
  if (rollYield > 0) return 'gain' // backwardation — positive carry
  if (rollYield < 0) return 'warn' // contango — headwind
  return 'neutral'
}

const TONE_CLASSES: Record<string, string> = {
  gain: 'text-gain',
  warn: 'text-warn',
  neutral: 'text-text-primary',
}

interface KpiCellProps {
  label: string
  children: ReactNode
  hint?: string
}

function KpiCell({ label, children, hint }: KpiCellProps) {
  return (
    <div className="flex flex-col gap-1" title={hint}>
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        {label}
      </span>
      <div className="font-mono text-sm">{children}</div>
    </div>
  )
}

export function CurveKPIRow({ snapshot, loading }: CurveKPIRowProps) {
  if (loading) {
    return (
      <div className="bg-bg-surface flex flex-wrap gap-8 rounded-lg border border-border-strong px-6 py-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-1">
            <Skeleton className="w-16 animate-shimmer h-3" />
            <Skeleton className="w-24 animate-shimmer h-5" />
          </div>
        ))}
      </div>
    )
  }

  const slopeTone = regimeTone(snapshot?.annualized_slope_pct ?? null)
  const rollT = rollTone(snapshot?.roll_yield_annualized ?? null)

  const slopeVal =
    snapshot?.annualized_slope_pct != null
      ? `${(snapshot.annualized_slope_pct * 100).toFixed(2)}%/yr`
      : '—'

  const rollVal =
    snapshot?.roll_yield_annualized != null
      ? `${(snapshot.roll_yield_annualized * 100).toFixed(2)}%/yr`
      : '—'

  const basisVal =
    snapshot?.basis != null
      ? `${snapshot.basis.toFixed(2)} (${((snapshot.basis_pct ?? 0) * 100).toFixed(2)}%)`
      : '—'

  return (
    <div className="bg-bg-surface flex flex-wrap gap-8 rounded-lg border border-border-strong px-6 py-4">
      <KpiCell label="Regime">
        <RegimeBadge regime={asRegime(snapshot?.regime)} />
      </KpiCell>

      <KpiCell label="Front Price" hint="Front contract settlement price">
        <span className="text-text-primary">
          {snapshot?.front_price != null ? fmt.price(snapshot.front_price, snapshot.asset) : '—'}
        </span>
      </KpiCell>

      <KpiCell label="Slope %/yr" hint="Annualized term structure slope">
        <span className={TONE_CLASSES[slopeTone]}>{slopeVal}</span>
      </KpiCell>

      <KpiCell label="Roll Yield" hint="Positive in backwardation (tailwind for longs)">
        <span className={TONE_CLASSES[rollT]}>{rollVal}</span>
      </KpiCell>

      <KpiCell label="Basis" hint="Continuous − front contract (pseudo-basis per ADR-001)">
        <span className="text-text-primary">{basisVal}</span>
      </KpiCell>
    </div>
  )
}
