import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ValidationRibbon } from '@/components/layout/ValidationRibbon'
import type { components } from '@/api/schema'

type DataFlag = components['schemas']['DataFlag']

const flagFixture: DataFlag[] = [
  { date: '2020-04-20', violation_type: 'negative_price', detail: 'Close -37.63 below zero' },
]

const twoFlagsFixture: DataFlag[] = [
  { date: '2020-04-20', violation_type: 'negative_price', detail: 'Close -37.63 below zero' },
  {
    date: '2021-02-24',
    violation_type: 'ohlc_consistency',
    detail: 'Close outside High-Low range',
  },
]

describe('ValidationRibbon', () => {
  it('renders singular "anomaly" for 1 flag', () => {
    render(<ValidationRibbon flags={flagFixture} onView={vi.fn()} />)
    expect(screen.getByText(/1 data anomaly/i)).toBeInTheDocument()
  })

  it('renders plural "anomalies" for 2 flags', () => {
    render(<ValidationRibbon flags={twoFlagsFixture} onView={vi.fn()} />)
    expect(screen.getByText(/2 data anomalies/i)).toBeInTheDocument()
  })

  it('calls onView when "View in Data Manager" is clicked', async () => {
    const onView = vi.fn()
    render(<ValidationRibbon flags={flagFixture} onView={onView} />)
    await userEvent.click(screen.getByText(/view in data manager/i))
    expect(onView).toHaveBeenCalledOnce()
  })

  it('dismiss button hides the ribbon', async () => {
    render(<ValidationRibbon flags={flagFixture} onView={vi.fn()} />)
    const dismissBtn = screen.getByRole('button', { name: /dismiss/i })
    await userEvent.click(dismissBtn)
    expect(screen.queryByText(/anomaly/i)).not.toBeInTheDocument()
  })
})
