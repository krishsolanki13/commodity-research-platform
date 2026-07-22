import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { StrategyPicker } from '@/components/inputs/StrategyPicker'
import { strategyCatalogFixture } from '../../mocks/fixtures/strategies'

const strategies = strategyCatalogFixture.strategies

describe('StrategyPicker', () => {
  test('renders all 4 strategies as cards', () => {
    render(<StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} />)
    expect(screen.getByText('EMA Crossover')).toBeInTheDocument()
    expect(screen.getByText('Momentum')).toBeInTheDocument()
    expect(screen.getByText('RSI Reversion')).toBeInTheDocument()
    expect(screen.getByText('Donchian Breakout')).toBeInTheDocument()
  })

  test('active strategy card has active visual state', () => {
    render(<StrategyPicker strategies={strategies} value="ema_crossover" onChange={vi.fn()} />)
    const activeCard = screen.getByText('EMA Crossover').closest('button')
    expect(activeCard).toHaveAttribute('data-active', 'true')
    expect(activeCard).toHaveAttribute('aria-pressed', 'true')
  })

  test('clicking a card calls onChange with strategy name', async () => {
    const onChange = vi.fn()
    render(<StrategyPicker strategies={strategies} value={null} onChange={onChange} />)
    await userEvent.click(screen.getByText('Momentum'))
    expect(onChange).toHaveBeenCalledWith('momentum')
  })
})
