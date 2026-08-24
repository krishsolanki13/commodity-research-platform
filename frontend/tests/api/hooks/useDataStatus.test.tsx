import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient as qc } from '@/app/queryClient'
import { useDataStatus } from '@/api/hooks/useDataStatus'
import { server } from '../../setup'

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => qc.clear())

afterEach(() => {
  server.resetHandlers()
})

describe('useDataStatus', () => {
  it('returns status with all 6 assets from fixture', async () => {
    const { result } = renderHook(() => useDataStatus(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(result.current.data?.assets).toHaveLength(6)
  })

  it('reports total_flags = 2 matching copper anomalies in fixture', async () => {
    const { result } = renderHook(() => useDataStatus(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })
    expect(result.current.data?.total_flags).toBe(2)
  })
})
