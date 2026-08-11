import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { SweepParamGridBuilder } from '@/features/sweeps/SweepParamGridBuilder'

describe('SweepParamGridBuilder', () => {
  it('shows error when fewer than 2 values entered', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <SweepParamGridBuilder
        paramNames={['fast_period']}
        paramTypes={{ fast_period: 'int' }}
        onChange={onChange}
      />,
    )

    const input = screen.getByPlaceholderText('e.g. 10, 20, 50, 100')
    await user.type(input, '10')

    await waitFor(() => {
      expect(
        screen.getByText('Enter at least 2 comma-separated values'),
      ).toBeInTheDocument()
    })
    expect(onChange).toHaveBeenCalledWith({ fast_period: [] }, false)
  })

  it('parses comma-separated ints correctly', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <SweepParamGridBuilder
        paramNames={['fast_period']}
        paramTypes={{ fast_period: 'int' }}
        onChange={onChange}
      />,
    )

    const input = screen.getByPlaceholderText('e.g. 10, 20, 50, 100')
    await user.type(input, '10, 20, 50')

    await waitFor(() => {
      const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1]
      expect(lastCall[0]).toEqual({ fast_period: [10, 20, 50] })
      expect(lastCall[1]).toBe(true)
    })
  })
})
