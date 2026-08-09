import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { StrategyPicker, isStrategyDisabled } from '@/components/inputs/StrategyPicker'
import { strategyCatalogFixture } from '../../mocks/fixtures/strategies'

const strategies = strategyCatalogFixture.strategies

describe('StrategyPicker', () => {
  test('renders all strategies as cards', () => {
    render(<StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} />)
    expect(screen.getByText('EMA Crossover')).toBeInTheDocument()
    expect(screen.getByText('Momentum')).toBeInTheDocument()
    expect(screen.getByText('RSI Reversion')).toBeInTheDocument()
    expect(screen.getByText('Donchian Breakout')).toBeInTheDocument()
    expect(screen.getByText('Carry')).toBeInTheDocument()
    expect(screen.getByText('WTI-Brent Spread')).toBeInTheDocument()
    expect(screen.getByText('COT Positioning')).toBeInTheDocument()
    expect(screen.getByText('EIA Inventory')).toBeInTheDocument()
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

  test('wti_brent_spread is disabled when asset is gold', () => {
    expect(isStrategyDisabled('wti_brent_spread', 'gold')).toBe(true)
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} asset="gold" />
    )
    const card = screen.getByText('WTI-Brent Spread').closest('button')
    expect(card).toHaveAttribute('data-disabled', 'true')
    expect(card).toHaveAttribute('aria-disabled', 'true')
  })

  test('wti_brent_spread is disabled when asset is brent', () => {
    expect(isStrategyDisabled('wti_brent_spread', 'brent')).toBe(true)
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} asset="brent" />
    )
    const card = screen.getByText('WTI-Brent Spread').closest('button')
    expect(card).toHaveAttribute('data-disabled', 'true')
  })

  test('wti_brent_spread is enabled when asset is wti', () => {
    expect(isStrategyDisabled('wti_brent_spread', 'wti')).toBe(false)
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} asset="wti" />
    )
    const card = screen.getByText('WTI-Brent Spread').closest('button')
    expect(card).not.toHaveAttribute('data-disabled')
    expect(card).toHaveAttribute('aria-disabled', 'false')
  })

  test('wti_brent_spread disabled: onClick does not select the strategy', async () => {
    const onChange = vi.fn()
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={onChange} asset="gold" />
    )
    await userEvent.click(screen.getByText('WTI-Brent Spread'))
    expect(onChange).not.toHaveBeenCalled()
  })

  test('carry is selectable for all assets (no constraint)', async () => {
    const onChange = vi.fn()
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={onChange} asset="gold" />
    )
    expect(isStrategyDisabled('carry', 'gold')).toBe(false)
    await userEvent.click(screen.getByText('Carry'))
    expect(onChange).toHaveBeenCalledWith('carry')
  })

  test('cot_positioning is selectable for brent (no constraint)', async () => {
    const onChange = vi.fn()
    render(
      <StrategyPicker
        strategies={strategies}
        value={null}
        onChange={onChange}
        asset="brent"
      />
    )
    expect(isStrategyDisabled('cot_positioning', 'brent')).toBe(false)
    await userEvent.click(screen.getByText('COT Positioning'))
    expect(onChange).toHaveBeenCalledWith('cot_positioning')
  })

  test('disabled wti_brent_spread shows tooltip text containing WTI', async () => {
    const user = userEvent.setup()
    render(
      <StrategyPicker strategies={strategies} value={null} onChange={vi.fn()} asset="gold" />
    )
    await user.hover(screen.getByText('WTI-Brent Spread'))
    const tips = await screen.findAllByText(/WTI-Brent spread requires WTI as the primary asset/i)
    expect(tips.length).toBeGreaterThan(0)
  })
})
