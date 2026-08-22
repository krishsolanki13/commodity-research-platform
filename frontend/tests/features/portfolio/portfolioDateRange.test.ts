import { describe, expect, it } from 'vitest'
import {
  isValidIsoDate,
  validatePortfolioDateRange,
} from '@/features/portfolio/portfolioUrlState'

describe('validatePortfolioDateRange', () => {
  it('accepts empty dates (full-history default)', () => {
    expect(validatePortfolioDateRange('', '')).toEqual({})
  })

  it('accepts a valid ordered range', () => {
    expect(validatePortfolioDateRange('2020-01-01', '2022-12-31')).toEqual({})
  })

  it('flags invalid from_date format', () => {
    expect(validatePortfolioDateRange('2020/01/01', '')).toEqual({
      fromDate: 'Invalid date format',
    })
  })

  it('flags invalid to_date format', () => {
    expect(validatePortfolioDateRange('', 'not-a-date')).toEqual({
      toDate: 'Invalid date format',
    })
  })

  it('flags to_date before from_date', () => {
    expect(validatePortfolioDateRange('2022-12-31', '2020-01-01')).toEqual({
      toDate: 'End date must be after start date',
    })
  })

  it('rejects impossible calendar dates', () => {
    expect(isValidIsoDate('2020-13-40')).toBe(false)
    expect(isValidIsoDate('2020-02-30')).toBe(false)
    expect(isValidIsoDate('2020-01-01')).toBe(true)
  })
})
