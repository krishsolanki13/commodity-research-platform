import { CorrelationHeatmapChart } from '@/components/charts/CorrelationHeatmapChart'
import { dec } from '@/lib/fmt'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']

interface PortfolioCorrelationPanelProps {
  correlation: CorrelationReportResponse | null
  loading?: boolean
  error?: ApiClientError | Error | null
}

export function PortfolioCorrelationPanel({
  correlation,
  loading,
  error,
}: PortfolioCorrelationPanelProps) {
  const assets = correlation ? Object.keys(correlation.correlation_matrix).sort() : []

  return (
    <div className="flex flex-col gap-6">
      <CorrelationHeatmapChart
        correlationMatrix={correlation?.correlation_matrix ?? {}}
        assets={assets}
        height={320}
        loading={loading}
        error={error}
      />

      <div className="flex gap-6 font-mono text-xs text-text-secondary">
        <span>
          Avg Correlation:{' '}
          <span className="text-text-primary">
            {correlation?.avg_pairwise_correlation != null
              ? dec(correlation.avg_pairwise_correlation, 3)
              : '—'}
          </span>
        </span>
        {correlation?.most_correlated_pair && (
          <span>
            Most:{' '}
            <span className="text-text-primary">
              {correlation.most_correlated_pair[0]} / {correlation.most_correlated_pair[1]} (
              {dec(correlation.most_correlated_pair[2], 2)})
            </span>
          </span>
        )}
        {correlation?.least_correlated_pair && (
          <span>
            Least:{' '}
            <span className="text-text-primary">
              {correlation.least_correlated_pair[0]} / {correlation.least_correlated_pair[1]} (
              {dec(correlation.least_correlated_pair[2], 2)})
            </span>
          </span>
        )}
      </div>
    </div>
  )
}
