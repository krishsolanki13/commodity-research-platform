import { cn } from '@/lib/cn'

// NOTE: Token names 'warn-500' and 'warn-900a' are per the transfer package final
// decision. If tokens.css uses 'amber-500'/'amber-900a' instead, update the
// styleMap below and the corresponding test expectation in RegimeBadge.test.tsx.

type Regime = 'contango' | 'backwardation' | 'flat'

export interface RegimeBadgeProps {
  regime: Regime | null
  size?: 'sm' | 'md'
  className?: string
}

const SIZE: Record<string, string> = {
  sm: 'px-2.5 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-sm',
}

// All class strings listed statically so Tailwind includes them in the build
const STYLE: Record<Regime, { classes: string; label: string }> = {
  contango: {
    classes: 'bg-accent-fill text-warn border-warn/30',
    label: 'CONTANGO',
  },
  backwardation: {
    classes: 'bg-gain-fill text-gain border-gain/30',
    label: 'BACKWARDATION',
  },
  flat: {
    classes: 'bg-bg-raised text-text-secondary border-border-strong',
    label: 'FLAT',
  },
}

export function RegimeBadge({ regime, size = 'md', className }: RegimeBadgeProps) {
  const base = cn(
    'inline-flex items-center rounded border font-mono font-medium tracking-wide',
    SIZE[size]
  )

  if (!regime) {
    return (
      <span
        role="status"
        aria-label="regime unknown"
        className={cn(base, 'border-border-strong bg-bg-raised text-text-disabled', className)}
      >
        —
      </span>
    )
  }

  const { classes, label } = STYLE[regime]

  return (
    <span role="status" aria-label={`${regime} regime`} className={cn(base, classes, className)}>
      {label}
    </span>
  )
}
