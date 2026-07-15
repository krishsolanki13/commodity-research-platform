import { cn } from '@/lib/cn'
import { rangeToDateParams, type RangePreset } from '@/lib/date-range'

interface DateRangePickerProps {
  value: { from: string; to: string }
  onChange: (value: { from: string; to: string }) => void
  presets?: string[]
  bounds?: { min?: string; max?: string }
  disabled?: boolean
  className?: string
}

const DEFAULT_PRESETS = ['1Y', '3Y', '5Y', 'MAX']

export function DateRangePicker({
  value,
  onChange,
  presets = DEFAULT_PRESETS,
  bounds,
  disabled,
  className,
}: DateRangePickerProps) {
  function handlePresetClick(preset: string) {
    const { from_date, to_date } = rangeToDateParams(preset as RangePreset)
    onChange({ from: from_date, to: to_date })
  }

  function clampDate(date: string, min?: string, max?: string): string {
    let result = date
    if (min && result < min) result = min
    if (max && result > max) result = max
    return result
  }

  function handleFromBlur(from: string) {
    const nextFrom = clampDate(from, bounds?.min, bounds?.max)
    let nextTo = value.to
    if (nextFrom > nextTo) nextTo = nextFrom
    onChange({ from: nextFrom, to: nextTo })
  }

  function handleToBlur(to: string) {
    const nextTo = clampDate(to, bounds?.min, bounds?.max)
    let nextFrom = value.from
    if (nextTo < nextFrom) nextFrom = nextTo
    onChange({ from: nextFrom, to: nextTo })
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <p className="text-sm text-text-secondary">
        {value.from} → {value.to}
      </p>

      <div className="flex flex-wrap gap-1">
        {presets.map((preset) => (
          <button
            key={preset}
            type="button"
            disabled={disabled}
            onClick={() => handlePresetClick(preset)}
            className={cn(
              'rounded-sm border border-border-strong px-2 py-1',
              'font-mono text-xs text-text-secondary',
              'hover:bg-bg-hover hover:text-text-primary',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
          >
            {preset}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          aria-label="From date"
          value={value.from}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          onBlur={(e) => handleFromBlur(e.target.value)}
          className={cn(
            'h-[var(--input-height)] flex-1 rounded-sm border border-border-strong bg-bg-app',
            'px-3 font-mono text-sm text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'disabled:cursor-not-allowed disabled:opacity-50'
          )}
        />
        <span className="text-xs text-text-secondary">→</span>
        <input
          type="text"
          aria-label="To date"
          value={value.to}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          onBlur={(e) => handleToBlur(e.target.value)}
          className={cn(
            'h-[var(--input-height)] flex-1 rounded-sm border border-border-strong bg-bg-app',
            'px-3 font-mono text-sm text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'disabled:cursor-not-allowed disabled:opacity-50'
          )}
        />
      </div>
    </div>
  )
}
