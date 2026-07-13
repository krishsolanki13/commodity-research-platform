/** True minus sign (U+2212) — visually distinct from hyphen */
export const MINUS = '\u2212'

const ASSET_DECIMALS: Record<string, number> = {
  gold: 2,
  silver: 3,
  copper: 4,
  wti: 2,
  brent: 2,
  natural_gas: 3,
}

export function price(value: number, asset: string): string {
  const decimals = ASSET_DECIMALS[asset] ?? 2
  if (value < 0) {
    return `${MINUS}${Math.abs(value).toFixed(decimals)}`
  }
  return value.toFixed(decimals)
}

export function percent(value: number, { showPlus = true }: { showPlus?: boolean } = {}): string {
  const pct = Math.abs(value * 100).toFixed(2)
  if (value < 0) return `${MINUS}${pct}%`
  if (value > 0 && showPlus) return `+${pct}%`
  return `${pct}%`
}

export function compactUsd(value: number): string {
  const sign = value < 0 ? MINUS : ''
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}k`
  return `${sign}$${abs.toFixed(0)}`
}

export function fullUsd(value: number): string {
  const sign = value < 0 ? MINUS : ''
  const abs = Math.abs(value)
  return `${sign}$${abs.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export function ratio(value: number): string {
  return value.toFixed(2)
}

export function ic(value: number): string {
  if (value < 0) return `${MINUS}${Math.abs(value).toFixed(3)}`
  return value.toFixed(3)
}

export function drawdown(value: number): string {
  return percent(value, { showPlus: false })
}

export function isoDate(value: string | number | Date): string {
  if (typeof value === 'string') return value.slice(0, 10)
  if (typeof value === 'number') return new Date(value).toISOString().slice(0, 10)
  return value.toISOString().slice(0, 10)
}

export function tradeBars(bars: number): string {
  if (bars >= 252) return `${(bars / 252).toFixed(1)}yr`
  if (bars >= 21) return `${Math.round(bars / 21)}mo`
  return `${bars}d`
}

export const fmt = {
  price,
  percent,
  compactUsd,
  fullUsd,
  ratio,
  ic,
  drawdown,
  isoDate,
  tradeBars,
}
