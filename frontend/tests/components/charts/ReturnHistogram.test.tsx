import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { ReturnHistogram } from '@/components/charts/ReturnHistogram'

const returns = Array.from({ length: 100 }, (_, i) => Math.sin(i * 0.1) * 0.01)

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ReturnHistogram', () => {
  it('renders without errors with 100 return values', () => {
    expect(() =>
      render(<ReturnHistogram values={returns} height={250} />, { wrapper: Wrapper })
    ).not.toThrow()
  })

  it('empty values array does not throw', () => {
    expect(() =>
      render(<ReturnHistogram values={[]} height={250} />, { wrapper: Wrapper })
    ).not.toThrow()
  })
})
