import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { AssetMetadataPanel } from '@/features/market/AssetMetadataPanel'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

const goldMeta: AssetMetadata = {
  name: 'gold',
  display_name: 'Gold',
  ticker_continuous: 'GC=F',
  contract_root: 'GC',
  exchange_suffix: 'CMX',
  exchange: 'COMEX',
  currency: 'USD',
  unit: 'troy_oz',
  contract_multiplier: 100,
  tick_size: 0.1,
  tick_value: 10.0,
}

describe('AssetMetadataPanel', () => {
  it('table element carries w-full class', () => {
    const { container } = render(<AssetMetadataPanel metadata={goldMeta} />)
    const table = container.querySelector('table')
    expect(table).toBeTruthy()
    expect(table?.className).toContain('w-full')
  })
})
