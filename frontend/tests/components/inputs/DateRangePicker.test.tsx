import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { DateRangePicker } from '@/components/inputs/DateRangePicker'
import { rangeToDateParams } from '@/lib/date-range'

describe('DateRangePicker', () => {
  test('renders from and to date strings in mono font', () => {
    render(<DateRangePicker value={{ from: '2015-01-01', to: '2026-07-15' }} onChange={vi.fn()} />)
    expect(screen.getByLabelText('From date')).toHaveClass('font-mono')
    expect(screen.getByLabelText('To date')).toHaveClass('font-mono')
    expect(screen.getByLabelText('From date')).toHaveValue('2015-01-01')
    expect(screen.getByLabelText('To date')).toHaveValue('2026-07-15')
  })

  test("clicking '1Y' preset calls onChange with computed ISO dates", async () => {
    const onChange = vi.fn()
    render(<DateRangePicker value={{ from: '2010-01-01', to: '2026-07-15' }} onChange={onChange} />)

    // Compute expected before click so both use the same "now"
    const expected = rangeToDateParams('1Y')
    await userEvent.click(screen.getByRole('button', { name: '1Y' }))

    expect(onChange).toHaveBeenCalledWith({
      from: expected.from_date,
      to: expected.to_date,
    })
  })

  test("preset buttons render (at least '1Y', '3Y', '5Y' visible)", () => {
    render(<DateRangePicker value={{ from: '2015-01-01', to: '2026-07-15' }} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: '1Y' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '3Y' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '5Y' })).toBeInTheDocument()
  })

  test('from input has min= when bounds.min is set', () => {
    render(
      <DateRangePicker
        value={{ from: '2024-09-27', to: '2026-07-15' }}
        onChange={vi.fn()}
        bounds={{ min: '2024-09-27' }}
      />
    )
    expect(screen.getByLabelText('From date')).toHaveAttribute('min', '2024-09-27')
  })

  test('MAX preset is clamped to bounds.min', async () => {
    const onChange = vi.fn()
    render(
      <DateRangePicker
        value={{ from: '2024-09-27', to: '2026-07-15' }}
        onChange={onChange}
        bounds={{ min: '2024-09-27' }}
      />
    )
    await userEvent.click(screen.getByRole('button', { name: 'MAX' }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ from: '2024-09-27' })
    )
  })
})
