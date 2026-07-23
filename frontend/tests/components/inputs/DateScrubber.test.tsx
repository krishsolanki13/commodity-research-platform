import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { DateScrubber } from '@/components/inputs/DateScrubber'

describe('DateScrubber', () => {
  it('renders Latest button in active state when value is null', () => {
    render(<DateScrubber value={null} onChange={vi.fn()} />)
    const latestBtn = screen.getByRole('button', {
      name: /use latest available date/i,
    })
    expect(latestBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('clicking Latest button calls onChange with null', async () => {
    const onChange = vi.fn()
    render(<DateScrubber value="2025-01-02" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: /use latest available date/i }))
    expect(onChange).toHaveBeenCalledWith(null)
  })

  it('date input change calls onChange with ISO string', () => {
    const onChange = vi.fn()
    render(
      <DateScrubber
        value="2025-06-01"
        onChange={onChange}
        minDate="2023-01-01"
        maxDate="2026-07-16"
      />
    )
    const input = screen.getByLabelText('Observation date')
    fireEvent.change(input, { target: { value: '2025-01-15' } })
    expect(onChange).toHaveBeenCalledWith('2025-01-15')
  })

  it('date input is enabled in Latest mode and click switches to today', () => {
    const onChange = vi.fn()
    render(<DateScrubber value={null} onChange={onChange} />)
    const input = screen.getByLabelText('Observation date')
    expect(input).not.toBeDisabled()
    fireEvent.click(input)
    expect(onChange).toHaveBeenCalledWith(new Date().toISOString().slice(0, 10))
  })
})
