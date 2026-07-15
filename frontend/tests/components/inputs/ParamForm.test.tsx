import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { ParamForm } from '@/components/inputs/ParamForm'
import type { components } from '@/api/schema'

type ParamSpec = components['schemas']['ParamSpec']

const emaCrossoverSchema: ParamSpec[] = [
  {
    name: 'fast_period',
    kind: 'int',
    default: 50,
    min: 5,
    max: 100,
    description: 'Fast EMA period',
    unit: 'bars',
  },
  {
    name: 'slow_period',
    kind: 'int',
    default: 200,
    min: 50,
    max: 500,
    description: 'Slow EMA period',
    unit: 'bars',
  },
]

const defaultValues = { fast_period: 50, slow_period: 200 }

describe('ParamForm', () => {
  test('renders int param fields with correct labels', () => {
    render(<ParamForm schema={emaCrossoverSchema} values={defaultValues} onChange={vi.fn()} />)
    expect(screen.getByText('fast_period')).toBeInTheDocument()
    expect(screen.getByText('slow_period')).toBeInTheDocument()
  })

  test('onChange called when valid value entered', async () => {
    const onChange = vi.fn()
    render(
      <ParamForm schema={emaCrossoverSchema} values={defaultValues} onChange={onChange} />
    )

    const fastInput = screen.getAllByRole('spinbutton')[0]
    await userEvent.clear(fastInput)
    await userEvent.type(fastInput, '75')
    await userEvent.tab()

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith({ fast_period: 75, slow_period: 200 })
    })
  })

  test('validation error shown for out-of-range value', async () => {
    render(<ParamForm schema={emaCrossoverSchema} values={defaultValues} onChange={vi.fn()} />)

    const fastInput = screen.getAllByRole('spinbutton')[0]
    await userEvent.clear(fastInput)
    await userEvent.type(fastInput, '1')
    await userEvent.tab()

    await waitFor(() => {
      expect(screen.getByText(/greater than or equal to 5/i)).toBeInTheDocument()
    })
  })

  test('reset button restores field to default value', async () => {
    render(<ParamForm schema={emaCrossoverSchema} values={defaultValues} onChange={vi.fn()} />)

    const fastInput = screen.getAllByRole('spinbutton')[0]
    await userEvent.clear(fastInput)
    await userEvent.type(fastInput, '75')
    expect(fastInput).toHaveValue(75)

    await userEvent.click(screen.getByRole('button', { name: 'Reset fast_period to default' }))
    expect(fastInput).toHaveValue(50)
  })
})
