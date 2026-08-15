import { useDataQC } from '@/api/hooks'

interface DataQCPanelProps {
  asset: string | null
}

const HEALTH_CONFIG: Record<string, { label: string; dotClass: string; textClass: string }> = {
  ok: {
    label: 'Healthy',
    dotClass: 'bg-gain',
    textClass: 'text-gain',
  },
  warn: {
    label: 'Warning',
    dotClass: 'bg-warn',
    textClass: 'text-warn',
  },
  crit: {
    label: 'Critical',
    dotClass: 'bg-loss',
    textClass: 'text-loss',
  },
}

export function DataQCPanel({ asset }: DataQCPanelProps) {
  const { data: qc, isLoading, error } = useDataQC(asset)

  if (!asset) return null

  if (isLoading) {
    return <div className="h-24 animate-pulse rounded border border-border-default bg-bg-raised" />
  }

  if (error || !qc) {
    return (
      <div className="rounded border border-border-default bg-bg-panel px-4 py-3">
        <p className="text-xs text-text-secondary">QC report unavailable.</p>
      </div>
    )
  }

  const health = HEALTH_CONFIG[qc.data_health] ?? HEALTH_CONFIG['warn']

  return (
    <div className="space-y-3">
      {/* Health badge row */}
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2 w-2 rounded-full ${health.dotClass}`} />
        <span className={`text-xs font-medium ${health.textClass}`}>{health.label}</span>
        <span className="text-xs text-text-secondary">
          {qc.bar_count?.toLocaleString() ?? '—'} bars · {qc.from_date ?? '—'} → {qc.to_date ?? '—'}
        </span>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          {
            label: 'OHLC VIOLATIONS',
            value: String(qc.ohlc_violations ?? 0),
            alert: (qc.ohlc_violations ?? 0) > 0,
          },
          {
            label: 'ZERO VOLUME DAYS',
            value: String(qc.zero_volume_days ?? 0),
            alert: false,
          },
          {
            label: 'LARGE GAP FLAGS',
            value: String(qc.large_gap_flags ?? 0),
            alert: (qc.large_gap_flags ?? 0) > 0,
          },
        ].map(({ label, value, alert }) => (
          <div key={label} className="rounded border border-border-default bg-bg-panel p-3">
            <p className="text-xs uppercase tracking-wider text-text-secondary">{label}</p>
            <p
              className={`mt-1 font-mono text-sm font-medium ${
                alert ? 'text-warn' : 'text-text-primary'
              }`}
            >
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Anomalies */}
      {qc.anomalies && qc.anomalies.length > 0 && (
        <div className="border-warn/30 bg-warn/5 space-y-1 rounded border p-3">
          <p className="text-xs font-medium uppercase tracking-wider text-warn">Anomalies</p>
          {qc.anomalies.map((anomaly, i) => (
            <p key={i} className="font-mono text-xs text-text-secondary">
              · {anomaly}
            </p>
          ))}
        </div>
      )}

      {(qc.ohlc_violations ?? 0) > 0 && (
        <p className="text-xs leading-relaxed text-text-secondary">
          Note: OHLC constraint flags are expected for Yahoo Finance continuous futures series —
          settlement prices are volume-weighted averages and may fall outside the intraday High/Low
          range (ADR-001 §3.1.4).
        </p>
      )}
    </div>
  )
}
