import { fmt } from '@/lib/fmt'
import { cn } from '@/lib/cn'

type ICBand = 'strong' | 'weak' | 'noise'

interface ICBandBadgeProps {
  ic: number | null | undefined
  className?: string
}

function getBand(ic: number | null | undefined): ICBand {
  if (ic === null || ic === undefined) return 'noise'
  const abs = Math.abs(ic)
  if (abs >= 0.05) return 'strong'
  if (abs >= 0.02) return 'weak'
  return 'noise'
}

const BAND_COLOR: Record<ICBand, string> = {
  strong: 'var(--ic-strong)',
  weak: 'var(--ic-weak)',
  noise: 'var(--ic-noise)',
}

// 15% opacity backgrounds — inline style because value is runtime-dynamic
const BAND_BG: Record<ICBand, string> = {
  strong: 'rgba(63,  182, 139, 0.15)',
  weak: 'rgba(217, 160, 60,  0.15)',
  noise: 'rgba(124, 138, 156, 0.15)',
}

export function ICBandBadge({ ic, className }: ICBandBadgeProps) {
  const band = getBand(ic)
  const color = BAND_COLOR[band]
  const bg = BAND_BG[band]
  const label = ic === null || ic === undefined ? '— · —' : `${fmt.ic(ic)} · ${band}`

  return (
    <span
      className={cn('px-1.5 py-0.5 rounded-sm font-mono text-xs', className)}
      style={{ backgroundColor: bg, color }}
    >
      {label}
    </span>
  )
}
