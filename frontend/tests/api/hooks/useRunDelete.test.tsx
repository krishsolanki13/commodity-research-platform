import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useRunDelete } from '@/api/hooks/useRunDelete'

describe('useRunDelete', () => {
  it('mutation succeeds and returns deleted: true', async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useRunDelete(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync('20260715_120000_ema_crossover_gold')
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})
