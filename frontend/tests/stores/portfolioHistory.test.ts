import { describe, it, expect, beforeEach } from 'vitest'
import { usePortfolioHistory } from '@/stores/portfolioHistory'

// Replicate the F7 comparisonBasket pattern exactly:
// reset both Zustand state and localStorage before each test to prevent persist bleed.
beforeEach(() => {
  usePortfolioHistory.setState({ runs: [], dismissedIds: [] })
  localStorage.clear()
})

const makeRun = (id: string, totalReturn: number | null = 0.015) => ({
  run_id: id,
  strategy: 'ema_crossover',
  executed_at: new Date().toISOString(),
  n_assets: 6,
  total_return: totalReturn,
})

describe('portfolioHistory store', () => {
  it('initial state has empty runs array', () => {
    expect(usePortfolioHistory.getState().runs).toHaveLength(0)
  })

  it('addRun prepends to front, deduplicates, and enforces max 10', () => {
    const { addRun } = usePortfolioHistory.getState()

    // Add same run twice — should not duplicate
    addRun(makeRun('run-1'))
    addRun(makeRun('run-1'))
    expect(usePortfolioHistory.getState().runs).toHaveLength(1)

    // Add 10 more distinct runs — oldest should be evicted
    for (let i = 2; i <= 12; i++) {
      addRun(makeRun(`run-${i}`))
    }
    const { runs } = usePortfolioHistory.getState()
    expect(runs).toHaveLength(10)
    // Most recent should be at the front
    expect(runs[0].run_id).toBe('run-12')
    // run-1 should have been evicted (added first, now oldest)
    expect(runs.some((r) => r.run_id === 'run-1')).toBe(false)
  })

  it('removeRun removes the entry; has() returns correct boolean', () => {
    const { addRun, removeRun, has } = usePortfolioHistory.getState()

    addRun(makeRun('run-A'))
    expect(has('run-A')).toBe(true)

    removeRun('run-A')
    expect(has('run-A')).toBe(false)
    expect(usePortfolioHistory.getState().runs).toHaveLength(0)
  })
})
