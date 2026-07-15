import { fmt } from '@/lib/fmt'

export type RangePreset = '1M' | '3M' | '6M' | '1Y' | '3Y' | '5Y' | 'MAX'

export const RANGE_PRESETS: RangePreset[] = ['1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX']

export function rangeToDateParams(range: RangePreset): { from_date: string; to_date: string } {
  const today = new Date()
  const from = new Date(today)

  switch (range) {
    case '1M':
      from.setMonth(today.getMonth() - 1)
      break
    case '3M':
      from.setMonth(today.getMonth() - 3)
      break
    case '6M':
      from.setMonth(today.getMonth() - 6)
      break
    case '1Y':
      from.setFullYear(today.getFullYear() - 1)
      break
    case '3Y':
      from.setFullYear(today.getFullYear() - 3)
      break
    case '5Y':
      from.setFullYear(today.getFullYear() - 5)
      break
    case 'MAX':
      return { from_date: '2010-01-01', to_date: fmt.isoDate(today) }
  }

  return { from_date: fmt.isoDate(from), to_date: fmt.isoDate(today) }
}
