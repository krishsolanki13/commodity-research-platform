import { cn } from '@/lib/cn'

interface DateScrubberProps {
  value: string | null
  onChange: (date: string | null) => void
  minDate?: string
  maxDate?: string
  disabled?: boolean
  className?: string
}

export function DateScrubber({
  value,
  onChange,
  minDate,
  maxDate,
  disabled = false,
  className,
}: DateScrubberProps) {
  const hideDateInput = minDate !== undefined && maxDate !== undefined && minDate > maxDate

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <button
        type="button"
        onClick={() => onChange(null)}
        aria-label="Use latest available date"
        aria-pressed={value === null}
        disabled={disabled}
        className={cn(
          'rounded-sm px-2 py-1 font-mono text-xs transition-colors duration-fast',
          'disabled:cursor-not-allowed disabled:opacity-50',
          value === null
            ? 'bg-accent font-medium text-bg-app'
            : 'border border-border-strong bg-bg-app text-text-secondary hover:bg-bg-hover'
        )}
      >
        Latest
      </button>

      {!hideDateInput && (
        <input
          type="date"
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value || null)}
          min={minDate}
          max={maxDate}
          disabled={disabled || value === null}
          aria-label="Observation date"
          className={cn(
            'rounded-sm border border-border-strong bg-bg-app px-2 py-1 font-mono text-xs',
            'text-text-primary disabled:cursor-not-allowed disabled:opacity-50',
            'focus:outline-none focus:ring-1 focus:ring-focus-ring',
            '[color-scheme:dark]'
          )}
        />
      )}
    </div>
  )
}
