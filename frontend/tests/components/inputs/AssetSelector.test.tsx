import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

const mockAssets: AssetMetadata[] = [
  {
    name: 'gold',
    display_name: 'Gold',
    ticker_continuous: 'GC=F',
    contract_root: 'GC',
    exchange_suffix: '',
    exchange: 'COMEX',
    currency: 'USD',
    unit: 'oz',
    contract_multiplier: 100,
    tick_size: 0.1,
    tick_value: 10,
  },
  {
    name: 'silver',
    display_name: 'Silver',
    ticker_continuous: 'SI=F',
    contract_root: 'SI',
    exchange_suffix: '',
    exchange: 'COMEX',
    currency: 'USD',
    unit: 'oz',
    contract_multiplier: 5000,
    tick_size: 0.005,
    tick_value: 25,
  },
  {
    name: 'wti',
    display_name: 'WTI Crude Oil',
    ticker_continuous: 'CL=F',
    contract_root: 'CL',
    exchange_suffix: '',
    exchange: 'NYMEX',
    currency: 'USD',
    unit: 'bbl',
    contract_multiplier: 1000,
    tick_size: 0.01,
    tick_value: 10,
  },
  {
    name: 'brent',
    display_name: 'Brent Crude',
    ticker_continuous: 'BZ=F',
    contract_root: 'BZ',
    exchange_suffix: '',
    exchange: 'ICE',
    currency: 'USD',
    unit: 'bbl',
    contract_multiplier: 1000,
    tick_size: 0.01,
    tick_value: 10,
  },
  {
    name: 'natural_gas',
    display_name: 'Natural Gas',
    ticker_continuous: 'NG=F',
    contract_root: 'NG',
    exchange_suffix: '',
    exchange: 'NYMEX',
    currency: 'USD',
    unit: 'mmBtu',
    contract_multiplier: 10000,
    tick_size: 0.001,
    tick_value: 10,
  },
  {
    name: 'copper',
    display_name: 'Copper',
    ticker_continuous: 'HG=F',
    contract_root: 'HG',
    exchange_suffix: '',
    exchange: 'COMEX',
    currency: 'USD',
    unit: 'lb',
    contract_multiplier: 25000,
    tick_size: 0.0005,
    tick_value: 12.5,
  },
]

describe('AssetSelector', () => {
  test('renders 6 options from mockAssets', async () => {
    render(<AssetSelector value={null} onChange={vi.fn()} assets={mockAssets} />)
    await userEvent.click(screen.getByRole('combobox'))
    for (const asset of mockAssets) {
      expect(screen.getByText(asset.display_name)).toBeInTheDocument()
    }
  })

  test('selecting an option calls onChange with the asset name', async () => {
    const onChange = vi.fn()
    render(<AssetSelector value={null} onChange={onChange} assets={mockAssets} />)
    await userEvent.click(screen.getByRole('combobox'))
    await userEvent.click(screen.getByText('Gold'))
    expect(onChange).toHaveBeenCalledWith('gold')
  })

  test('search input filters to matching options only', async () => {
    render(<AssetSelector value={null} onChange={vi.fn()} assets={mockAssets} />)
    await userEvent.click(screen.getByRole('combobox'))
    await userEvent.type(screen.getByPlaceholderText('Search...'), 'Gold')
    expect(screen.getByText('Gold')).toBeInTheDocument()
    expect(screen.queryByText('Silver')).not.toBeInTheDocument()
  })
})
