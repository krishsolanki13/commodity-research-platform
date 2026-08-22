import { z } from 'zod'

export const portfolioUrlSchema = z.object({
  run_id: z.string().optional(),
  strategy: z.string().default('ema_crossover'),
  sizing_method: z
    .enum(['fixed_notional', 'volatility_scaled'])
    .default('fixed_notional'),
  initial_capital: z.coerce.number().default(1_000_000),
  from_date: z.string().optional(),
  to_date: z.string().optional(),
})

export const portfolioUrlDefaults: z.infer<typeof portfolioUrlSchema> = {
  run_id: undefined,
  strategy: 'ema_crossover',
  sizing_method: 'fixed_notional',
  initial_capital: 1_000_000,
  from_date: undefined,
  to_date: undefined,
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/

/** Returns true when value is a real calendar date in YYYY-MM-DD form. */
export function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE_RE.test(value)) return false
  const [y, m, d] = value.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d
}

export type PortfolioDateRangeErrors = {
  fromDate?: string
  toDate?: string
}

/**
 * Inline (non-blocking) validation for optional portfolio date range.
 * Empty strings are valid — omit both from the launch request.
 */
export function validatePortfolioDateRange(
  fromDate: string,
  toDate: string
): PortfolioDateRangeErrors {
  const errors: PortfolioDateRangeErrors = {}

  if (fromDate && !isValidIsoDate(fromDate)) {
    errors.fromDate = 'Invalid date format'
  }
  if (toDate && !isValidIsoDate(toDate)) {
    errors.toDate = 'Invalid date format'
  }

  if (
    fromDate &&
    toDate &&
    isValidIsoDate(fromDate) &&
    isValidIsoDate(toDate) &&
    toDate < fromDate
  ) {
    errors.toDate = 'End date must be after start date'
  }

  return errors
}
