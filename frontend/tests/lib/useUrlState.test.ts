import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { z } from 'zod'
import React from 'react'
import { useUrlState } from '@/lib/useUrlState'

const schema = z.object({
  asset: z.string().default('gold'),
  range: z.string().default('1Y'),
  page: z.coerce.number().int().min(1).default(1),
})
type State = z.infer<typeof schema>
const defaults: State = { asset: 'gold', range: '1Y', page: 1 }

function makeWrapper(search: string) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(MemoryRouter, { initialEntries: [`/?${search}`] }, children)
  }
}

describe('useUrlState', () => {
  it('parses valid string params from URL', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('asset=silver&range=3Y'),
    })
    expect(result.current[0].asset).toBe('silver')
    expect(result.current[0].range).toBe('3Y')
  })

  it('coerces numeric params', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('page=3'),
    })
    expect(result.current[0].page).toBe(3)
  })

  it('falls back to defaults when params are missing', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper(''),
    })
    expect(result.current[0]).toEqual(defaults)
  })

  it('falls back to defaults when params are invalid', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('page=not-a-number'),
    })
    expect(result.current[0]).toEqual(defaults)
  })

  it('setState updates a single param without clearing others', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('asset=copper&range=5Y&page=2'),
    })
    act(() => {
      result.current[1]({ page: 3 })
    })
    expect(result.current[0].asset).toBe('copper')
    expect(result.current[0].range).toBe('5Y')
    expect(result.current[0].page).toBe(3)
  })

  it('setState removes param when value is null (explicit clear)', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('asset=copper&range=5Y'),
    })
    act(() => {
      result.current[1]({ range: null })
    })
    expect(result.current[0].range).toBe('1Y')
  })

  it('setState preserves existing param when value is undefined (no-op)', () => {
    const { result } = renderHook(() => useUrlState(schema, defaults), {
      wrapper: makeWrapper('asset=copper&range=5Y'),
    })
    act(() => {
      result.current[1]({ range: undefined })
    })
    expect(result.current[0].range).toBe('5Y')
  })
})
