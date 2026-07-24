import { MetricGrid } from '@/components/data/MetricGrid'
import type { components } from '@/api/schema'

type PortfolioMetrics = components['schemas']['PortfolioSummaryResponse']['portfolio_metrics']

interface PortfolioKPIRowProps {
  metrics: PortfolioMetrics | null
  loading?: boolean
}

export function PortfolioKPIRow({ metrics, loading }: PortfolioKPIRowProps) {
  return (
    <MetricGrid
      loading={loading}
      columns={6}
      metrics={[
        {
          label: 'SHARPE',
          value: metrics?.['sharpe'],
          format: 'ic',
          tone: 'neutral',
        },
        {
          label: 'MAX DD',
          value: metrics?.['max_drawdown'],
          format: 'drawdown',
        },
        {
          label: 'TOTAL RETURN',
          value: metrics?.['total_return'],
          format: 'percent',
        },
        {
          label: 'CAGR',
          value: metrics?.['cagr'],
          format: 'percent',
        },
        {
          label: 'PORTFOLIO VOL',
          value: metrics?.['portfolio_vol'],
          format: 'percent',
          tone: 'neutral',
        },
      ]}
    />
  )
}
