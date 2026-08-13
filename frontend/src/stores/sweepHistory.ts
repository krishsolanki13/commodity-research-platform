import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface SweepHistoryState {
  sweepIds: string[]
  addSweep: (id: string) => void
  clearAll: () => void
}

export const useSweepHistory = create<SweepHistoryState>()(
  persist(
    (set) => ({
      sweepIds: [],
      addSweep: (id) =>
        set((state) => ({
          sweepIds: [id, ...state.sweepIds.filter((s) => s !== id)].slice(0, 10),
        })),
      clearAll: () => set({ sweepIds: [] }),
    }),
    {
      name: 'commodity-research-sweep-history',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
