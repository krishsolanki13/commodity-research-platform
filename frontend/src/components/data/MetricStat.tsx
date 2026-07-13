import { Info } from 'lucide-react'
import { fmt } from '@/lib/fmt'
import { tone } from '@/lib/tone'
import { cn } from '@/lib/cn'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'

type MetricFormat =
  | 'percent'
  | 'ratio'
  | 'ic'
  | 'drawdown'
  | 'compactUsd'
  | 'fullUsd'
  | 'bars'
  | 'integer'
  | 'raw'

interface MetricStatProps {
  label: string
  value: number | null | undefined
  format: MetricFormat
  delta?: number
  deltaFormat?: 'percent' | 'ratio'
  tone?: 'auto' | 'neutral'
  size?: 'md' | 'lg'
  hint?: string
  className?: string
}

function formatValue(value: number, format: MetricFormat): string {
  switch (format) {
    case 'percent':    return fmt.percent(value)
    case 'ratio':      return fmt.ratio(value)
    case 'ic':         return fmt.ic(value)
    case 'drawdown':   return fmt.drawdown(value)
    case 'compactUsd': return fmt.compactUsd(value)
    case 'fullUsd':    return fmt.fullUsd(value)
    case 'bars':       return fmt.tradeBars(value)
    case 'integer':    return Math.round(value).toString()
    case 'raw':        return String(value)
  }
}

function getValueColor(
  value: number | null | undefined,
  format: MetricFormat,
  toneProp: 'auto' | 'neutral'
): string {
  if (value === null || value === undefined) return 'var(--text-secondary)'
  // Drawdown is always a loss metric regardless of tone prop
  if (format === 'drawdown') return 'var(--text-loss)'
  if (toneProp === 'neutral') return 'var(--text-primary)'
  // auto tone
  if (format === 'ic') return tone.ic(value)
  if (
    format === 'percent' ||
    format === 'compactUsd' ||
    format === 'fullUsd'
  ) {
    return tone.pnl(value)
  }
  // ratio, bars, integer, raw — no sign semantics
  return 'var(--text-primary)'
}

export function MetricStat({
  label,
  value,
  format,
  delta,
  deltaFormat = 'percent',
  tone: toneProp = 'auto',
  size = 'md',
  hint,
  className,
}: MetricStatProps) {
  const color = getValueColor(value, format, toneProp)
  const isEmpty = value === null || value === undefined

  return (
    <TooltipProvider delayDuration={300}>
      <div className={cn('flex flex-col gap-0.5', className)}>
        {/* Label row */}
        <div className="flex items-center gap-1">
          <span className="text-xs uppercase tracking-wider text-text-secondary">
            {label}
          </span>
          {hint && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-help">
                  <Info size={12} strokeWidth={1.75} className="text-text-secondary" />
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs font-mono text-xs">{hint}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Value */}
        <span
          style={{ color }}
          className={cn(
            'font-mono font-medium',
            size === 'lg' ? 'text-metric-lg' : 'text-metric'
          )}
        >
          {isEmpty ? '—' : formatValue(value, format)}
        </span>

        {/* Delta */}
        {delta !== undefined && !isEmpty && (
          <span
            style={{ color: tone.pnl(delta) }}
            className="font-mono text-xs"
          >
            {deltaFormat === 'percent'
              ? fmt.percent(delta)
              : fmt.ratio(delta)}
          </span>
        )}
      </div>
    </TooltipProvider>
  )
}

export type { MetricStatProps, MetricFormat }
