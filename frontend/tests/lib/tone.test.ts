import { describe, it, expect } from 'vitest'
import { tone } from '@/lib/tone'

describe('tone.pnl', () => {
  it('returns gain token for positive value', () => {
    expect(tone.pnl(100)).toBe('var(--text-gain)')
  })
  it('returns loss token for negative value', () => {
    expect(tone.pnl(-50)).toBe('var(--text-loss)')
  })
  it('returns secondary token for zero', () => {
    expect(tone.pnl(0)).toBe('var(--text-secondary)')
  })
})

describe('tone.ic', () => {
  it('returns strong token at exactly 0.05 boundary', () => {
    expect(tone.ic(0.05)).toBe('var(--ic-strong)')
  })
  it('returns weak token at exactly 0.02 boundary', () => {
    expect(tone.ic(0.02)).toBe('var(--ic-weak)')
  })
  it('returns noise token below 0.02', () => {
    expect(tone.ic(0.0123)).toBe('var(--ic-noise)')
  })
  it('uses absolute value — negative IC at 0.08 is strong', () => {
    expect(tone.ic(-0.08)).toBe('var(--ic-strong)')
  })
  it('returns noise token for null (missing evaluation)', () => {
    expect(tone.ic(null)).toBe('var(--ic-noise)')
  })
})

describe('tone.status', () => {
  it('returns info token for running status', () => {
    expect(tone.status('running')).toBe('var(--info-500)')
  })
})
