import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { FeatureSpecTable } from '@/components/data/FeatureSpecTable'

const mockSpecs = [
  {
    indicator_name: 'ema',
    params: { period: 50 },
    column_name: 'ema_50',
    asset: 'gold',
    computed_at: '2026-07-15T00:00:00Z',
  },
  {
    indicator_name: 'ema',
    params: { period: 200 },
    column_name: 'ema_200',
    asset: 'gold',
    computed_at: '2026-07-15T00:00:00Z',
  },
]

describe('FeatureSpecTable', () => {
  test('renders correct column values for each spec', () => {
    render(<FeatureSpecTable specs={mockSpecs} />)
    expect(screen.getAllByText('ema').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('ema_50')).toBeInTheDocument()
    expect(screen.getByText('ema_200')).toBeInTheDocument()
  })

  test('column_name rendered with accent color class', () => {
    render(<FeatureSpecTable specs={mockSpecs} />)
    const ema50 = screen.getByText('ema_50')
    const ema200 = screen.getByText('ema_200')
    expect(ema50).toHaveClass('text-accent')
    expect(ema200).toHaveClass('text-accent')
  })
})
