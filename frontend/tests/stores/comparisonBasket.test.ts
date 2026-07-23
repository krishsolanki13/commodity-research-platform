import { describe, it, expect, beforeEach } from 'vitest'
import { useComparisonBasket, MAX_COMPARISON_SIZE } from '@/stores/comparisonBasket'

describe('comparisonBasket store', () => {
  beforeEach(() => {
    useComparisonBasket.setState({ ids: [] })
  })

  it('initial state has empty ids array', () => {
    const { ids } = useComparisonBasket.getState()
    expect(ids).toEqual([])
  })

  it('add inserts an id; second add of same id is no-op', () => {
    const { add } = useComparisonBasket.getState()
    add('run-1')
    expect(useComparisonBasket.getState().ids).toEqual(['run-1'])
    add('run-1')
    expect(useComparisonBasket.getState().ids).toHaveLength(1)
  })

  it('remove deletes an id; toggle flips membership', () => {
    useComparisonBasket.setState({ ids: ['run-1', 'run-2'] })
    const { remove, toggle } = useComparisonBasket.getState()
    remove('run-1')
    expect(useComparisonBasket.getState().ids).toEqual(['run-2'])
    toggle('run-2')
    expect(useComparisonBasket.getState().ids).toEqual([])
    toggle('run-3')
    expect(useComparisonBasket.getState().ids).toEqual(['run-3'])
  })

  it('clear empties basket; max enforced — 9th add silently ignored', () => {
    const fullIds = Array.from({ length: MAX_COMPARISON_SIZE }, (_, i) => `run-${i}`)
    useComparisonBasket.setState({ ids: fullIds })
    const { add, clear } = useComparisonBasket.getState()
    add('run-overflow')
    expect(useComparisonBasket.getState().ids).toHaveLength(MAX_COMPARISON_SIZE)
    clear()
    expect(useComparisonBasket.getState().ids).toEqual([])
  })

  it('has and ids reflect add/remove membership', () => {
    const basket = useComparisonBasket.getState()
    basket.add('run_001')
    expect(useComparisonBasket.getState().has('run_001')).toBe(true)
    expect(useComparisonBasket.getState().ids).toContain('run_001')
    useComparisonBasket.getState().remove('run_001')
    expect(useComparisonBasket.getState().has('run_001')).toBe(false)
  })
})
