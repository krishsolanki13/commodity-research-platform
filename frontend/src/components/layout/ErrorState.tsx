import { AlertCircle } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from '@/ui/button'

interface ErrorLike {
  code?: string
  message: string
}

interface ErrorStateProps {
  error: ErrorLike | Error
  onRetry?: () => void
  compact?: boolean
  className?: string
}

function extractError(error: ErrorLike | Error): { code?: string; message: string } {
  if (error instanceof Error) {
    return { message: error.message }
  }
  return { code: error.code, message: error.message }
}

export function ErrorState({
  error,
  onRetry,
  compact = false,
  className,
}: ErrorStateProps) {
  const { code, message } = extractError(error)

  if (compact) {
    return (
      <div className={cn('flex items-center gap-3 px-4 py-2', className)}>
        <AlertCircle size={16} strokeWidth={1.75} className="shrink-0 text-crit" />
        <div className="flex flex-1 flex-col">
          {code && (
            <span className="font-mono text-xs text-text-secondary">{code}</span>
          )}
          <span className="text-sm text-text-primary">{message}</span>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 p-8',
        className
      )}
    >
      <AlertCircle size={48} strokeWidth={1.5} className="text-crit" />
      <div className="flex flex-col items-center gap-1 text-center">
        {code && (
          <span className="font-mono text-xs text-text-secondary">{code}</span>
        )}
        <p className="text-sm text-text-primary">{message}</p>
      </div>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}
