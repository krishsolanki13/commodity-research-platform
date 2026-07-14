import { cn } from '@/lib/cn'
import { Skeleton } from '@/ui/skeleton'

type SkeletonVariant = 'metric-grid' | 'chart' | 'table' | 'form'

interface LoadingSkeletonProps {
  variant: SkeletonVariant
  rows?: number
  columns?: 3 | 4 | 6
  className?: string
}

const gridColsClass: Record<number, string> = {
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  6: 'grid-cols-6',
}

export function LoadingSkeleton({
  variant,
  rows = 5,
  columns = 4,
  className,
}: LoadingSkeletonProps) {
  if (variant === 'metric-grid') {
    return (
      <div
        data-variant="metric-grid"
        className={cn('grid gap-4', gridColsClass[columns], className)}
      >
        {Array.from({ length: columns * 2 }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn('animate-shimmer', i % 2 === 0 ? 'w-16 h-3' : 'w-24 h-6')}
          />
        ))}
      </div>
    )
  }

  if (variant === 'chart') {
    return (
      <div data-variant="chart" className={cn('relative', className)}>
        <Skeleton className="animate-shimmer h-[55vh] w-full rounded-md" />
        <Skeleton className="h-0.5 animate-shimmer absolute bottom-6 left-6 w-[calc(100%-3rem)]" />
        <Skeleton className="w-0.5 animate-shimmer absolute bottom-6 left-6 h-[calc(55vh-1.5rem)]" />
      </div>
    )
  }

  if (variant === 'table') {
    return (
      <div data-variant="table" className={cn('flex flex-col gap-2', className)}>
        <Skeleton className="animate-shimmer h-8 w-full rounded-sm" />
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="animate-shimmer h-10 w-full rounded-sm" />
        ))}
      </div>
    )
  }

  // form
  return (
    <div data-variant="form" className={cn('flex flex-col gap-4', className)}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="gap-1.5 flex flex-col">
          <Skeleton className="w-24 animate-shimmer h-3" />
          <Skeleton className="animate-shimmer h-8 w-full rounded-sm" />
        </div>
      ))}
    </div>
  )
}
