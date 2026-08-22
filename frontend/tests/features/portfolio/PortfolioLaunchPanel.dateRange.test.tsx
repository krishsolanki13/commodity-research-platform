import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PortfolioLaunchPanel } from '@/features/portfolio/PortfolioLaunchPanel'

const mutateAsync = vi.fn()

vi.mock('@/api/hooks', () => ({
  usePortfolioLaunch: () => ({
    mutateAsync,
    isPending: false,
  }),
  usePortfolioStatus: () => ({ data: undefined }),
}))

function renderPanel(props: { fromDate?: string; toDate?: string } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <PortfolioLaunchPanel
        strategy="ema_crossover"
        params={{ fast_period: 50, slow_period: 200 }}
        sizingMethod="fixed_notional"
        initialCapital={1_000_000}
        fromDate={props.fromDate ?? ''}
        toDate={props.toDate ?? ''}
        onLaunched={() => undefined}
      />
    </QueryClientProvider>
  )
}

describe('PortfolioLaunchPanel date range request body', () => {
  beforeEach(() => {
    mutateAsync.mockReset()
    mutateAsync.mockResolvedValue({ run_id: 'poll_test' })
  })

  it('omits from_date/to_date when both empty', async () => {
    const user = userEvent.setup()
    renderPanel()
    await user.click(screen.getByRole('button', { name: /launch portfolio backtest/i }))
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled())
    const body = mutateAsync.mock.calls[0][0] as Record<string, unknown>
    expect(body).not.toHaveProperty('from_date')
    expect(body).not.toHaveProperty('to_date')
  })

  it('includes from_date and to_date when set', async () => {
    const user = userEvent.setup()
    renderPanel({ fromDate: '2020-01-01', toDate: '2022-12-31' })
    await user.click(screen.getByRole('button', { name: /launch portfolio backtest/i }))
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled())
    const body = mutateAsync.mock.calls[0][0] as Record<string, unknown>
    expect(body.from_date).toBe('2020-01-01')
    expect(body.to_date).toBe('2022-12-31')
  })
})
