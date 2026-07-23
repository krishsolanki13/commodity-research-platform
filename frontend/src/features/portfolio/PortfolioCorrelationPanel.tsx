import { CorrelationHeatmapChart } from '@/components/charts/CorrelationHeatmapChart'
import type { ApiClientError } from '@/api/client'
import type { components } from '@/api/schema'

type CorrelationReportResponse = components['schemas']['CorrelationReportResponse']
type PortfolioSummaryResponse = components['schemas']['PortfolioSummaryResponse']

function isApiError(error: unknown): error is ApiClientError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'apiError' in error &&
    typeof (error as ApiClientError).apiError?.status === 'number'
  )
}

interface PortfolioCorrelationPanelProps {
  correlation: CorrelationReportResponse | null
  summary?: PortfolioSummaryResponse | null
  loading?: boolean
  error?: ApiClientError | Error | null
}

export function PortfolioCorrelationPanel({
  correlation,
  summary,
  loading,
  error,
}: PortfolioCorrelationPanelProps) {
  const isServerRestartLoss =
    !!error && isApiError(error) && error.apiError.status === 404 && !!summary

  if (isServerRestartLoss) {
    return (
      <div className="flex items-center gap-2 p-4 text-xs text-text-secondary">
        <span>Detailed analytics unavailable after server restart.</span>
        <span className="ml-1 text-text-secondary">Re-run the portfolio analysis to restore.</span>
      </div>
    )
  }

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
            {correlation?.avg_pairwise_correlation?.toFixed(3) ?? '—'}
          </span>
        </span>
        {correlation?.most_correlated_pair && (
          <span>
            Most:{' '}
            <span className="text-text-primary">
              {correlation.most_correlated_pair[0]} / {correlation.most_correlated_pair[1]} (
              {correlation.most_correlated_pair[2].toFixed(2)})
            </span>
          </span>
        )}
        {correlation?.least_correlated_pair && (
          <span>
            Least:{' '}
            <span className="text-text-primary">
              {correlation.least_correlated_pair[0]} / {correlation.least_correlated_pair[1]} (
              {correlation.least_correlated_pair[2].toFixed(2)})
            </span>
          </span>
        )}
      </div>
    </div>
  )
}
