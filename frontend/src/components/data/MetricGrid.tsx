import { cn } from '@/lib/cn'
import { MetricStat, type MetricStatProps } from '@/components/data/MetricStat'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'

interface MetricGridProps {
  metrics: MetricStatProps[]
  columns?: 3 | 4 | 6
  loading?: boolean
  className?: string
}

const gridColsClass: Record<number, string> = {
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  6: 'grid-cols-6',
}

export function MetricGrid({ metrics, columns = 4, loading = false, className }: MetricGridProps) {
  if (loading) {
    return <LoadingSkeleton variant="metric-grid" columns={columns} className={className} />
  }

  return (
    <div className={cn('grid w-full gap-4', gridColsClass[columns], className)}>
      {metrics.map((metric, i) => (
        <MetricStat key={i} {...metric} className={cn('min-w-0', metric.className)} />
      ))}
    </div>
  )
}
