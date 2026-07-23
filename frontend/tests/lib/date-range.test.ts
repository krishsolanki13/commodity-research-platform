import { describe, it, expect } from 'vitest'
import { rangeToDateParams } from '@/lib/date-range'

describe('rangeToDateParams', () => {
  it('MAX returns 2010-01-01 as from_date', () => {
    const result = rangeToDateParams('MAX')
    expect(result.from_date).toBe('2010-01-01')
  })

  it('1Y returns a from_date whose year is currentYear - 1', () => {
    const result = rangeToDateParams('1Y')
    expect(new Date(result.from_date).getFullYear()).toBe(new Date().getFullYear() - 1)
  })
})
