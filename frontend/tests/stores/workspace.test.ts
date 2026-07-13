import { beforeEach, describe, test, expect } from 'vitest'
import { useWorkspace } from '@/stores/workspace'

beforeEach(() => {
  // Reset to initial state before each test
  useWorkspace.setState({
    theme: 'dark',
    density: 'compact',
    navCollapsed: false,
  })
  localStorage.clear()
})

describe('workspace store', () => {
  test('initial state is dark compact expanded', () => {
    const state = useWorkspace.getState()
    expect(state.theme).toBe('dark')
    expect(state.density).toBe('compact')
    expect(state.navCollapsed).toBe(false)
  })

  test('setTheme updates theme and DOM data attribute', () => {
    useWorkspace.getState().setTheme('light')
    expect(useWorkspace.getState().theme).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  test('toggleNavCollapsed flips state both ways', () => {
    useWorkspace.getState().toggleNavCollapsed()
    expect(useWorkspace.getState().navCollapsed).toBe(true)
    useWorkspace.getState().toggleNavCollapsed()
    expect(useWorkspace.getState().navCollapsed).toBe(false)
  })

  test('persisted to localStorage under correct key', () => {
    useWorkspace.getState().setDensity('comfortable')
    const raw = localStorage.getItem('commodity-research-workspace')
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw!)).toMatchObject({
      state: { density: 'comfortable' },
    })
  })
})
