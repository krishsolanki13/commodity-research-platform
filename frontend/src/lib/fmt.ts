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
    return `${MINUS}${new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(Math.abs(value))}`
  }
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function percent(value: number, { showPlus = true }: { showPlus?: boolean } = {}): string {
  const pct = Math.abs(value * 100).toFixed(2)
  if (value < 0) return `${MINUS}${pct}%`
  if (value > 0 && showPlus) return `+${pct}%`
  return `${pct}%`
}

/** Unsigned magnitude percent — value is a fraction (0.08 → "8.0%"). */
export function pct(value: number, precision: number = 1): string {
  return `${(value * 100).toFixed(precision)}%`
}

export function dec(value: number, precision: number = 2): string {
  // Exponential round avoids IEEE half-even quirks in Number#toFixed (e.g. 3.815 → "3.81")
  return Number(Math.round(Number(`${value}e${precision}`)) + `e-${precision}`).toFixed(precision)
}

export function num(value: number, decimals: number = 2): string {
  if (!isFinite(value)) return '—'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
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

/** Format epoch milliseconds as YYYY-MM-DD (UTC). Coerces numeric strings from category axes. */
export const fmtDate = (ms: number): string => {
  const n = Number(ms)
  if (!Number.isFinite(n)) return String(ms ?? '')
  return new Date(n).toISOString().slice(0, 10)
}

export function tradeBars(bars: number): string {
  return `${Math.round(bars)} bars`
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
