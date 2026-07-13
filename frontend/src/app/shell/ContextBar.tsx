import { useSearchParams } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'

export function ContextBar() {
  const [searchParams] = useSearchParams()
  const asset = searchParams.get('asset')
  const fromDate = searchParams.get('from_date')
  const toDate = searchParams.get('to_date')

  return (
    <div
      role="complementary"
      aria-label="Research context"
      className={cn(
        'flex h-10 shrink-0 items-center gap-3 border-b border-border-default px-4',
        'bg-bg-app text-xs text-text-secondary'
      )}
    >
      {asset !== null && (
        <>
          <span className="rounded-sm bg-bg-raised px-2 py-0.5 font-mono text-text-accent">
            {asset}
          </span>
          {fromDate !== null && toDate !== null && (
            <span className="text-text-secondary">
              {fmt.isoDate(fromDate)} → {fmt.isoDate(toDate)}
            </span>
          )}
        </>
      )}
    </div>
  )
}
