import { z } from 'zod'
import type { components } from '@/api/schema'
import { FuturesCurveChart } from '@/components/charts/FuturesCurveChart'
import { useUrlState } from '@/lib/useUrlState'

type FuturesCurveResponse = components['schemas']['FuturesCurveResponse']
type Regime = 'contango' | 'backwardation' | 'flat' | null

const panelSchema = z.object({ asset: z.string().optional() })
const panelDefaults = {}

function asRegime(value: string | null | undefined): Regime {
  if (value === 'contango' || value === 'backwardation' || value === 'flat') return value
  return null
}

export interface CurvePanelProps {
  snapshot: FuturesCurveResponse | null
  loading?: boolean
  error?: Error | null
}

export function CurvePanel({ snapshot, loading, error }: CurvePanelProps) {
  const [{ asset }] = useUrlState(panelSchema, panelDefaults)

  return (
    <div className="bg-bg-surface flex flex-col gap-2 rounded-lg border border-border-strong p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        Forward Curve
      </span>

      <FuturesCurveChart
        points={snapshot?.points ?? []}
        regime={asRegime(snapshot?.regime)}
        asset={asset ?? snapshot?.asset ?? ''}
        height={280}
        loading={loading}
        error={error}
        empty={{ message: 'No contract data for this asset.' }}
      />

      <span
        className="font-mono text-xs text-text-secondary"
        title="Latest available settlement data"
      >
        Observation date: {snapshot?.observation_date ?? '—'}
      </span>
    </div>
  )
}
