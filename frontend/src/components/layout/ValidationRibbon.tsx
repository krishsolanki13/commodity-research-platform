import { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type DataFlag = components['schemas']['DataFlag']

interface ValidationRibbonProps {
  flags: DataFlag[]
  onView: () => void
  className?: string
}

export function ValidationRibbon({ flags, onView, className }: ValidationRibbonProps) {
  const [isDismissed, setIsDismissed] = useState(false)

  if (isDismissed) return null

  return (
    <div
      className={cn(
        'flex items-center gap-3 border-l-[3px] border-warn bg-bg-raised px-4 py-2',
        className
      )}
    >
      <AlertTriangle size={14} strokeWidth={1.75} className="shrink-0 text-warn" />
      <span className="text-xs text-text-primary">
        {flags.length} data {flags.length === 1 ? 'anomaly' : 'anomalies'} flagged in this range.
      </span>
      <button
        onClick={onView}
        className="ml-auto text-xs text-text-accent underline hover:text-accent-hover"
      >
        View in Data Manager →
      </button>
      <button
        onClick={() => setIsDismissed(true)}
        aria-label="Dismiss"
        className="text-text-secondary hover:text-text-primary"
      >
        <X size={14} strokeWidth={1.75} />
      </button>
    </div>
  )
}
