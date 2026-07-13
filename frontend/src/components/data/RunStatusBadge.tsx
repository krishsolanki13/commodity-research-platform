import { cn } from '@/lib/cn'
import { tone } from '@/lib/tone'

type RunStatus = 'queued' | 'running' | 'complete' | 'failed'

interface RunStatusBadgeProps {
  status: RunStatus
  className?: string
}

export function RunStatusBadge({ status, className }: RunStatusBadgeProps) {
  const color = tone.status(status)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-xs',
        className
      )}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          status === 'running' && 'animate-pulse-dot'
        )}
        style={{ backgroundColor: color }}
      />
      <span style={{ color }}>{status}</span>
    </span>
  )
}
