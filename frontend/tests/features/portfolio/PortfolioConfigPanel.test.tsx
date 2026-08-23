import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PortfolioConfigPanel } from '@/features/portfolio/PortfolioConfigPanel'
import { rangeToDateParams } from '@/lib/date-range'

function renderPanel(overrides: Partial<Parameters<typeof PortfolioConfigPanel>[0]> = {}) {
  const onDateRangeChange = vi.fn()
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <PortfolioConfigPanel
        strategy="ema_crossover"
        onStrategyChange={vi.fn()}
        sizingMethod="fixed_notional"
        onSizingChange={vi.fn()}
        initialCapital={1_000_000}
        onCapitalChange={vi.fn()}
        fromDate=""
        toDate=""
        onDateRangeChange={onDateRangeChange}
        {...overrides}
      />
    </QueryClientProvider>
  )
  return { onDateRangeChange }
}

describe('PortfolioConfigPanel date presets', () => {
  it('clicking 1Y sets from/to via parent callback', async () => {
    const user = userEvent.setup()
    const { onDateRangeChange } = renderPanel()
    const expected = rangeToDateParams('1Y')
    await user.click(screen.getByRole('button', { name: '1Y' }))
    expect(onDateRangeChange).toHaveBeenCalledWith({
      from: expected.from_date,
      to: expected.to_date,
    })
  })

  it('clicking MAX clears both dates', async () => {
    const user = userEvent.setup()
    const { onDateRangeChange } = renderPanel({
      fromDate: '2020-01-01',
      toDate: '2022-12-31',
    })
    await user.click(screen.getByRole('button', { name: 'MAX' }))
    expect(onDateRangeChange).toHaveBeenCalledWith({ from: '', to: '' })
  })
})
