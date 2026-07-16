import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const MAX_BASKET_SIZE = 8

interface ComparisonBasketState {
  ids: string[]
  add: (id: string) => void
  remove: (id: string) => void
  toggle: (id: string) => void
  clear: () => void
  has: (id: string) => boolean
}

export const useComparisonBasket = create<ComparisonBasketState>()(
  persist(
    (set, get) => ({
      ids: [],

      add: (id) =>
        set((s) => {
          if (s.ids.includes(id) || s.ids.length >= MAX_BASKET_SIZE) return s
          return { ids: [...s.ids, id] }
        }),

      remove: (id) => set((s) => ({ ids: s.ids.filter((x) => x !== id) })),

      toggle: (id) => {
        const { ids, add, remove } = get()
        if (ids.includes(id)) {
          remove(id)
        } else {
          add(id)
        }
      },

      has: (id) => get().ids.includes(id),

      clear: () => set({ ids: [] }),
    }),
    {
      name: 'commodity-research-comparison-basket',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ ids: s.ids }),
    }
  )
)

export const MAX_COMPARISON_SIZE = MAX_BASKET_SIZE
