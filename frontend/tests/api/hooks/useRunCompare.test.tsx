import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { useRunCompare } from '@/api/hooks/useRunCompare'

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('useRunCompare', () => {
  it('returns CompareResponse with 2 runs and aligned_series', async () => {
    const { result } = renderHook(() => useRunCompare(['run-a', 'run-b']), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.runs).toHaveLength(2)
    expect(result.current.data?.aligned_series).toHaveLength(2)
  })

  it('is disabled when fewer than 2 ids provided', () => {
    const { result } = renderHook(() => useRunCompare(['run-a']), { wrapper: makeWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
