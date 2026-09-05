export type RunStatus = 'queued' | 'running' | 'persisting' | 'complete' | 'failed'
export type IcBand = 'strong' | 'inverse_meaningful' | 'weak_positive' | 'weak_inverse' | 'noise'
export type Regime = 'contango' | 'backwardation' | 'flat'

export function pnlTone(value: number): string {
  if (value > 0) return 'var(--text-gain)'
  if (value < 0) return 'var(--text-loss)'
  return 'var(--text-secondary)'
}

export function directionTone(signal: 1 | -1 | 0): string {
  if (signal > 0) return 'var(--text-gain)'
  if (signal < 0) return 'var(--text-loss)'
  return 'var(--text-secondary)'
}

export function icTone(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'var(--ic-noise)'
  const abs = Math.abs(value)
  if (abs >= 0.05) return 'var(--ic-strong)'
  if (abs >= 0.02) return 'var(--ic-weak)'
  return 'var(--ic-noise)'
}

export function icBandTone(band: IcBand): string {
  if (band === 'strong' || band === 'inverse_meaningful') return 'var(--ic-strong)'
  if (band === 'weak_positive' || band === 'weak_inverse') return 'var(--ic-weak)'
  return 'var(--ic-noise)'
}

export function statusTone(status: RunStatus): string {
  const map: Record<RunStatus, string> = {
    queued: 'var(--text-secondary)',
    running: 'var(--info-500)',
    persisting: 'var(--info-500)',
    complete: 'var(--ok-500)',
    failed: 'var(--crit-500)',
  }
  return map[status] ?? 'var(--text-secondary)'
}

export function regimeTone(regime: Regime): string {
  if (regime === 'contango') return 'var(--text-loss)'
  if (regime === 'backwardation') return 'var(--text-gain)'
  return 'var(--text-secondary)'
}

export const tone = {
  pnl: pnlTone,
  direction: directionTone,
  ic: icTone,
  icBand: icBandTone,
  status: statusTone,
  regime: regimeTone,
}
