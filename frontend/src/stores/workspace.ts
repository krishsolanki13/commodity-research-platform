import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface WorkspaceState {
  theme: 'dark' | 'light'
  density: 'compact' | 'comfortable'
  navCollapsed: boolean
  setTheme: (theme: 'dark' | 'light') => void
  setDensity: (density: 'compact' | 'comfortable') => void
  toggleNavCollapsed: () => void
}

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set) => ({
      theme: 'dark',
      density: 'compact',
      navCollapsed: false,

      setTheme: (theme) => {
        set({ theme })
        document.documentElement.dataset.theme = theme
      },

      setDensity: (density) => {
        set({ density })
        document.documentElement.dataset.density = density
      },

      toggleNavCollapsed: () =>
        set((state) => ({ navCollapsed: !state.navCollapsed })),
    }),
    {
      name: 'commodity-research-workspace',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        density: state.density,
        navCollapsed: state.navCollapsed,
      }),
    }
  )
)
