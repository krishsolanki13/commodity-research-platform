import { useState } from 'react'
import type { components } from '@/api/schema'
import { PortfolioRollingCorrelationChart } from '@/components/charts/PortfolioRollingCorrelationChart'
import { cn } from '@/lib/cn'

type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']

interface Props {
  correlation: CorrelationReportResponse | null
  loading?: boolean
}

export function PortfolioRollingCorrelationPanel({ correlation, loading }: Props) {
  const [corrWindow, setCorrWindow] = useState<63 | 126>(63)

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-mono">Rolling Correlations — Top 5 Pairs</span>
        <div role="group" aria-label="Rolling window" className="flex gap-1">
          {([63, 126] as const).map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setCorrWindow(w)}
              aria-pressed={corrWindow === w}
              className={cn(
                'px-3 py-1 text-xs font-mono rounded transition-colors',
                corrWindow === w
                  ? 'bg-accent-fill text-primary'
                  : 'text-secondary hover:text-primary'
              )}
            >
              {w}-day
            </button>
          ))}
        </div>
      </div>

      <PortfolioRollingCorrelationChart
        rollingCorrelations={
          corrWindow === 63
            ? (correlation?.rolling_correlations_63 ?? {})
            : (correlation?.rolling_correlations_126 ?? {})
        }
        correlationMatrix={correlation?.correlation_matrix ?? {}}
        windowDays={corrWindow}
        height={280}
        loading={loading}
        empty={{ message: 'No rolling correlation data available.' }}
      />

      <p className="mt-2 text-xs font-mono text-secondary">
        Showing top 5 asset pairs by absolute pairwise correlation.
      </p>
    </section>
  )
}
