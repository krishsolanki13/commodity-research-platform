import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/app/queryClient'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { goldEmaEvalFixture } from '../../mocks/fixtures/signal-eval'
import type { components } from '@/api/schema'

type DecayEntry = components['schemas']['DecayEntry']

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ICDecayChart', () => {
  it('renders ChartFrame wrapper without errors with decay fixture', () => {
    render(<ICDecayChart decay={goldEmaEvalFixture.evaluation.decay} />, {
      wrapper: Wrapper,
    })
    expect(document.body).not.toBeEmptyDOMElement()
  })

  it('does not throw when a horizon has null IC', () => {
    const decayWithNull: DecayEntry[] = [
      { horizon: 1, ic: 0.012 },
      { horizon: 2, ic: null },
      { horizon: 5, ic: 0.007 },
      { horizon: 10, ic: 0.004 },
      { horizon: 20, ic: 0.002 },
    ]
    expect(() => render(<ICDecayChart decay={decayWithNull} />, { wrapper: Wrapper })).not.toThrow()
  })

  it('passes loading state through to ChartFrame', () => {
    render(<ICDecayChart decay={goldEmaEvalFixture.evaluation.decay} loading={true} />, {
      wrapper: Wrapper,
    })
    expect(document.querySelector('.animate-shimmer')).toBeTruthy()
  })
})
