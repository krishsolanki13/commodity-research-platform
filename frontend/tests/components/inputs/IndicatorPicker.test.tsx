import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { IndicatorPicker } from '@/components/inputs/IndicatorPicker'
import { indicatorCatalogFixture } from '../../mocks/fixtures/indicators'
import type { components } from '@/api/schema'

type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']

const catalog = indicatorCatalogFixture.indicators

describe('IndicatorPicker', () => {
  test('renders indicators from catalog', () => {
    render(<IndicatorPicker catalog={catalog} selected={[]} onChange={vi.fn()} />)
    expect(screen.getByText('Exponential Moving Average')).toBeInTheDocument()
    expect(screen.getByText('Simple Moving Average')).toBeInTheDocument()
    expect(screen.getByText('Relative Strength Index')).toBeInTheDocument()
    expect(screen.getByText('Relative Vigor Index')).toBeInTheDocument()
    expect(screen.getByText('Momentum')).toBeInTheDocument()
  })

  test('selected spec chip shows resolved column name', () => {
    render(
      <IndicatorPicker
        catalog={catalog}
        selected={[{ name: 'ema', params: { period: 50 } }]}
        onChange={vi.fn()}
      />
    )
    expect(screen.getByText('ema_50')).toBeInTheDocument()
  })

  test('required spec chip has no remove button', () => {
    render(
      <IndicatorPicker
        catalog={catalog}
        selected={[]}
        requiredSpecs={[{ name: 'ema', params: { period: 50 } }]}
        onChange={vi.fn()}
      />
    )
    expect(screen.getByText('ema_50')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /remove ema_50/i })).not.toBeInTheDocument()
  })

  test('adding same spec twice does not duplicate it', async () => {
    let selected: FeatureSpecRequest[] = []
    const onChange = vi.fn((next: FeatureSpecRequest[]) => {
      selected = next
    })

    const { rerender } = render(
      <IndicatorPicker catalog={catalog} selected={selected} onChange={onChange} />
    )

    await userEvent.click(screen.getByText('Exponential Moving Average'))
    await userEvent.click(screen.getByRole('button', { name: 'Add indicator' }))
    // Default period from catalog is 20
    expect(onChange).toHaveBeenCalledWith([{ name: 'ema', params: { period: 20 } }])

    onChange.mockClear()
    rerender(<IndicatorPicker catalog={catalog} selected={selected} onChange={onChange} />)
    expect(screen.getByText('ema_20')).toBeInTheDocument()

    await userEvent.click(screen.getByText('Exponential Moving Average'))
    await userEvent.click(screen.getByRole('button', { name: 'Add indicator' }))

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getAllByText('ema_20')).toHaveLength(1)
  })
})
