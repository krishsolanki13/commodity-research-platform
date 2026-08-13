/**
 * Client-side portfolio run history.
 * No /api/portfolio/list endpoint exists in F0.
 * Zustand persist store — same pattern as comparisonBasket (F7).
 * Max 10 recent runs; FIFO eviction when full.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const MAX_HISTORY = 10

export interface PortfolioRunRecord {
  run_id: string
  strategy: string
  executed_at: string // ISO datetime
  n_assets: number // number of assets in the run
  total_return: number | null // from summary (for display in selector)
}

interface PortfolioHistoryState {
  runs: PortfolioRunRecord[]
  /** Run IDs known to 404 — filtered from API-backed selectors. */
  dismissedIds: string[]
  addRun: (run: PortfolioRunRecord) => void
  removeRun: (runId: string) => void
  clear: () => void
  has: (runId: string) => boolean
  isDismissed: (runId: string) => boolean
}

export const usePortfolioHistory = create<PortfolioHistoryState>()(
  persist(
    (set, get) => ({
      runs: [],
      dismissedIds: [],

      addRun: (run) =>
        set((s) => {
          // Remove duplicate if already present
          const filtered = s.runs.filter((r) => r.run_id !== run.run_id)
          // Add to front; evict oldest if over max
          const updated = [run, ...filtered].slice(0, MAX_HISTORY)
          return {
            runs: updated,
            dismissedIds: s.dismissedIds.filter((id) => id !== run.run_id),
          }
        }),

      removeRun: (runId) =>
        set((s) => ({
          runs: s.runs.filter((r) => r.run_id !== runId),
          dismissedIds: [runId, ...s.dismissedIds.filter((id) => id !== runId)].slice(0, 50),
        })),

      clear: () => set({ runs: [], dismissedIds: [] }),

      has: (runId) => get().runs.some((r) => r.run_id === runId),

      isDismissed: (runId) => get().dismissedIds.includes(runId),
    }),
    {
      name: 'commodity-research-portfolio-history',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ runs: s.runs, dismissedIds: s.dismissedIds }),
    }
  )
)

export const MAX_PORTFOLIO_HISTORY = MAX_HISTORY
