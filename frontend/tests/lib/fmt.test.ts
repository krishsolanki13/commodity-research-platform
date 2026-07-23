import { describe, it, expect } from 'vitest'
import { fmt, fmtDate, MINUS } from '@/lib/fmt'

describe('fmt.price', () => {
  it('formats gold with 2 decimal places', () => {
    expect(fmt.price(2450.5, 'gold')).toBe('2450.50')
  })
  it('formats copper with 4 decimal places', () => {
    expect(fmt.price(4.1234, 'copper')).toBe('4.1234')
  })
  it('formats natural_gas with 3 decimal places', () => {
    expect(fmt.price(2.156, 'natural_gas')).toBe('2.156')
  })
  it('uses true minus for negative price (WTI 2020-04-20)', () => {
    expect(fmt.price(-37.63, 'wti')).toBe(`${MINUS}37.63`)
  })
})

describe('fmt.percent', () => {
  it('shows + prefix for positive values', () => {
    expect(fmt.percent(0.0124)).toBe('+1.24%')
  })
  it('uses true minus for negative values', () => {
    expect(fmt.percent(-0.0087)).toBe(`${MINUS}0.87%`)
  })
  it('omits + when showPlus=false', () => {
    expect(fmt.percent(0.05, { showPlus: false })).toBe('5.00%')
  })
})

describe('fmt.compactUsd', () => {
  it('formats millions with 2dp', () => {
    expect(fmt.compactUsd(1_240_000)).toBe('$1.24M')
  })
  it('formats thousands with 1dp', () => {
    expect(fmt.compactUsd(182_400)).toBe('$182.4k')
  })
  it('formats small amounts without abbreviation', () => {
    expect(fmt.compactUsd(450)).toBe('$450')
  })
})

describe('fmt.isoDate', () => {
  it('returns YYYY-MM-DD from ISO string', () => {
    expect(fmt.isoDate('2026-07-06T14:22:33Z')).toBe('2026-07-06')
  })
})

describe('fmtDate', () => {
  it('formats epoch ms to ISO date', () => {
    expect(fmtDate(1262563200000)).toBe('2010-01-04')
    expect(fmtDate(0)).toBe('1970-01-01')
  })

  it('coerces numeric strings', () => {
    expect(fmtDate('1262563200000' as unknown as number)).toBe('2010-01-04')
  })
})

describe('fmt.tradeBars', () => {
  it('rounds and suffixes bars', () => {
    expect(fmt.tradeBars(8.85)).toBe('9 bars')
    expect(fmt.tradeBars(1.0)).toBe('1 bars')
  })
})
