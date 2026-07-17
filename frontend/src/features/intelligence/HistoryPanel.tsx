import { useCurveHistory } from '@/api/hooks/useCurveHistory'
import { TermStructureHistoryChart } from '@/components/charts/TermStructureHistoryChart'

export interface HistoryPanelProps {
  asset: string
  fromDate: string
  toDate: string
  nContracts: number
}

export function HistoryPanel({ asset, fromDate, toDate, nContracts }: HistoryPanelProps) {
  const { data, isLoading, error } = useCurveHistory(asset, fromDate, toDate, nContracts)

  return (
    <div className="bg-bg-surface flex flex-col gap-2 rounded-lg border border-border-strong p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        Term Structure History
      </span>

      <TermStructureHistoryChart
        snapshots={data?.snapshots ?? []}
        height={320}
        loading={isLoading}
        error={error ?? null}
        syncGroup="intelligence"
      />

      {data && (
        <span className="font-mono text-xs text-text-secondary">
          {data.from_date} → {data.to_date} · {data.snapshots.length} observations
        </span>
      )}
    </div>
  )
}
