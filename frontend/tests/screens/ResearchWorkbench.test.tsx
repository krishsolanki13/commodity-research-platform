import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient as qc } from '@/app/queryClient'
import { goldEmaEvalFixture } from '../mocks/fixtures/signal-eval'
import { strategyCatalogFixture } from '../mocks/fixtures/strategies'
import { ApiClientError } from '@/api/client'
import ResearchWorkbenchScreen from '@/screens/research/ResearchWorkbench'

const { mutateAsync } = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
}))

vi.mock('@/api/hooks/useEvaluateChainMutation', () => ({
  useEvaluateChainMutation: (onProgress?: (p: unknown) => void) => ({
    mutateAsync: (params: unknown) => {
      onProgress?.({ step: 'features', stepIndex: 1 })
      onProgress?.({ step: 'signal', stepIndex: 2 })
      onProgress?.({ step: 'evaluation', stepIndex: 3 })
      return mutateAsync(params) as Promise<unknown>
    },
    isPending: false,
  }),
  isEvaluateChainAsyncLaunch: (result: object) => 'job_id' in result,
}))

function buildMockEvalResult() {
  return {
    features: {
      asset: 'gold',
      from_date: '2015-01-01',
      to_date: '2026-07-15',
      bars: 3,
      specs: [
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
      ],
      columns: { index: [] as number[], columns: {} },
    },
    signal: {
      asset: 'gold',
      strategy: 'ema_crossover',
      params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
      bars: 3,
      raw_signal: {
        index: [1609459200000, 1609545600000, 1609632000000],
        columns: { raw: [0.5, -0.3, 0.8] },
      },
      position_signal: {
        index: [1609459200000, 1609545600000, 1609632000000],
        columns: { position: [1, -1, 1] },
      },
    },
    evaluation: goldEmaEvalFixture,
    evaluatedAt: '2026-07-15T00:00:00Z',
  }
}

function Wrapper({ initialEntry = '/research' }: { initialEntry?: string }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/research" element={<ResearchWorkbenchScreen />} />
          <Route path="/backtest/new" element={<div>Backtest New</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const emaUrl =
  '/research?asset=gold&strategy=ema_crossover' +
  '&params=' +
  encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200, signal_threshold: 0.0 })) +
  '&features=' +
  encodeURIComponent(
    JSON.stringify([
      { name: 'ema', params: { period: 50 } },
      { name: 'ema', params: { period: 200 } },
    ])
  )

beforeEach(() => {
  qc.clear()
  mutateAsync.mockReset()
  mutateAsync.mockResolvedValue(buildMockEvalResult())
})

describe('ResearchWorkbenchScreen', () => {
  it('renders config rail with strategy picker loaded from API', async () => {
    render(<Wrapper />)
    await waitFor(
      () => {
        for (const s of strategyCatalogFixture.strategies) {
          expect(screen.getAllByText(s.display_name).length).toBeGreaterThan(0)
        }
      },
      { timeout: 5000 }
    )
  })

  it('renders evaluate panel prompt before evaluation', () => {
    render(<Wrapper />)
    expect(
      screen.getByText(/Assemble features and a signal, then click Evaluate/i)
    ).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /chart/i })).not.toBeInTheDocument()
  })

  it('ICGateStrip renders in locked/null state when no evaluation exists', () => {
    render(<Wrapper />)
    expect(screen.getByText(/Backtest without evaluation/i)).toBeInTheDocument()
    const configureBtn = screen.getByRole('button', { name: /Configure backtest/i })
    expect(configureBtn).toBeDisabled()
  })

  it('after evaluate chain completes, evidence canvas shows evaluation results', async () => {
    const user = userEvent.setup()
    render(<Wrapper initialEntry={emaUrl} />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )

    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled(), { timeout: 5000 })
    await waitFor(
      () => {
        expect(screen.getByText('IC Decay')).toBeInTheDocument()
        expect(screen.getAllByText('0.012').length).toBeGreaterThan(0)
      },
      { timeout: 5000 }
    )
  })

  it('evaluation error renders inline error message', async () => {
    const user = userEvent.setup()
    mutateAsync.mockRejectedValueOnce(new Error('At least one indicator spec is required.'))
    render(<Wrapper initialEntry={emaUrl} />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )

    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(() => expect(mutateAsync).toHaveBeenCalled(), { timeout: 5000 })
    await waitFor(
      () => {
        const alert = screen.getByRole('alert')
        expect(alert).toHaveTextContent(/Signal evaluation failed/i)
        expect(alert).toHaveTextContent(/At least one indicator spec is required/i)
      },
      { timeout: 5000 }
    )
    // Stay on config view — no silent success / empty IC gate flip
    expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeInTheDocument()
    expect(screen.queryByText('IC Decay')).not.toBeInTheDocument()
  })

  it('changing a param after evaluation does not show a staleness chip', async () => {
    const user = userEvent.setup()
    render(<Wrapper initialEntry={emaUrl} />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))
    await waitFor(() => expect(screen.getByText('IC Decay')).toBeInTheDocument(), {
      timeout: 5000,
    })

    // Return to config to edit params — full-width results hide the form
    await user.click(screen.getByRole('button', { name: /Modify signal/i }))
    const fastInput = screen.getAllByRole('spinbutton')[0]
    await user.clear(fastInput)
    await user.type(fastInput, '40')
    await user.tab()

    expect(screen.queryByText(/Configuration changed — re-evaluate/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Config changed — click Evaluate/i)).not.toBeInTheDocument()
  })

  it('?asset=gold in URL pre-selects Gold in AssetSelector', async () => {
    render(<Wrapper initialEntry="/research?asset=gold" />)
    await waitFor(
      () => {
        const combo = screen.getByRole('combobox')
        expect(combo).toHaveTextContent('Gold')
      },
      { timeout: 5000 }
    )
  })

  it('does not crash from regime chip presence after initial render', async () => {
    render(<Wrapper />)
    await waitFor(
      () => expect(screen.queryAllByText(/EMA|Momentum|RSI|signal/i).length).toBeGreaterThan(0),
      { timeout: 5000 }
    )
    expect(screen.queryByText(/crashed|Uncaught/i)).not.toBeInTheDocument()
  })

  it('shows Evaluating elapsed counter while the mutation is in flight', async () => {
    const user = userEvent.setup()
    mutateAsync.mockImplementation(() => new Promise(() => {}))
    render(<Wrapper initialEntry={emaUrl} />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(() => expect(screen.getByText(/Evaluating\.\.\. \d+s/)).toBeInTheDocument(), {
      timeout: 5000,
    })
    expect(screen.queryByText('Queued...')).not.toBeInTheDocument()
    expect(screen.queryByText('IC Decay')).not.toBeInTheDocument()
  })

  it('shows Queued... for carry while the async launch mutation is in flight', async () => {
    const user = userEvent.setup()
    mutateAsync.mockImplementation(() => new Promise(() => {}))
    render(<Wrapper initialEntry="/research?asset=gold&strategy=carry" />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(() => expect(screen.getByText('Queued...')).toBeInTheDocument(), {
      timeout: 5000,
    })
    expect(screen.queryByText(/Evaluating\.\.\. \d+s/)).not.toBeInTheDocument()
  })

  it('shows results after carry async job completes', async () => {
    const user = userEvent.setup()
    const mock = buildMockEvalResult()
    mutateAsync.mockResolvedValue({
      job_id: 'job-carry-1',
      features: mock.features,
      signal: mock.signal,
    })
    render(<Wrapper initialEntry="/research?asset=gold&strategy=carry" />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(
      () => {
        expect(screen.getByText('IC Decay')).toBeInTheDocument()
        expect(screen.getAllByText('0.012').length).toBeGreaterThan(0)
      },
      { timeout: 5000 }
    )
  })

  it('does not show obsolete carry window clamp notice', async () => {
    render(
      <Wrapper initialEntry="/research?asset=gold&strategy=carry&from_date=2015-01-01" />
    )
    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    expect(
      screen.queryByText(/Carry evaluation is clamped to a 2-year window/i)
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Select 1Y for an unclamped result/i)).not.toBeInTheDocument()
  })

  it('shows curve coverage notice and min= for Carry', async () => {
    render(<Wrapper initialEntry="/research?asset=gold&strategy=carry" />)
    await waitFor(
      () =>
        expect(
          screen.getByText(/Carry requires futures curve data available from 2024-09-27/)
        ).toBeInTheDocument(),
      { timeout: 5000 }
    )
    expect(screen.getByLabelText('From date')).toHaveAttribute('min', '2024-09-27')
  })

  it('does not show curve coverage notice for ema_crossover', async () => {
    render(<Wrapper initialEntry={emaUrl} />)
    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    expect(
      screen.queryByText(/Carry requires futures curve data available from/)
    ).not.toBeInTheDocument()
    expect(screen.getByLabelText('From date')).not.toHaveAttribute('min')
  })

  it('shows INSUFFICIENT_CURVE_COVERAGE as an inline date-range error', async () => {
    const user = userEvent.setup()
    mutateAsync.mockRejectedValueOnce(
      new ApiClientError({
        code: 'INSUFFICIENT_CURVE_COVERAGE',
        message:
          'Requested window starts 2015-01-01, but curve data for gold is only available from 2024-09-27 onward.',
        detail: '2024-09-27',
        status: 400,
      })
    )
    render(<Wrapper initialEntry="/research?asset=gold&strategy=carry" />)

    await waitFor(
      () => expect(screen.getByRole('button', { name: /Evaluate signal/i })).toBeEnabled(),
      { timeout: 5000 }
    )
    await user.click(screen.getByRole('button', { name: /Evaluate signal/i }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent(
        'Curve data for gold starts 2024-09-27 — adjust date range'
      )
    })
  })
})
