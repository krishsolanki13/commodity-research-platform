import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import type { ReactNode } from 'react'
import { CurveDateControl } from '@/features/intelligence/CurveDateControl'

function makeWrapper(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('CurveDateControl', () => {
  it('renders date control with Latest button when asset is in URL', async () => {
    render(<CurveDateControl />, {
      wrapper: makeWrapper('/intelligence?asset=gold'),
    })
    // findByRole is async — retries until found or timeout
    await expect(
      screen.findByRole('button', { name: /use latest available date/i }, { timeout: 5000 })
    ).resolves.toBeInTheDocument()
  })

  it('renders nothing when no asset is selected', () => {
    render(<CurveDateControl />, {
      wrapper: makeWrapper('/intelligence'),
    })
    expect(
      screen.queryByRole('button', { name: /use latest available date/i })
    ).not.toBeInTheDocument()
  })
})
