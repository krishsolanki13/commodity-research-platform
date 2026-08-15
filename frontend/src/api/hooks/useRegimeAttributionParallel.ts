import { useQueries } from '@tanstack/react-query'
import { client } from '@/api/client'
import { qk } from '@/api/queryKeys'
import type { components } from '@/api/schema'

type RegimeAttributionResponse = components['schemas']['RegimeAttributionResponse']

/**
 * Parallel prefetch for all asset regime attributions.
 * NOT CURRENTLY USED — see TD-FEP-REGIME-ASYNC.
 *
 * Single-worker Uvicorn saturates under 6 concurrent 30–90s synchronous
 * requests. This hook fires all assets simultaneously which blocks the
 * entire server — Strategy Builder, Research Workbench, and all other
 * API calls queue behind the regime computations.
 *
 * Enable when backend ships POST /api/regime-attribution/compute
 * (async job pattern — same as backtests and portfolio runs).
 * Frontend upgrade is a one-line import swap in PortfolioRegimePanel.tsx:
 *
 *   Before: import { useRegimeAttribution } from '@/api/hooks/useRegimeAttribution'
 *   After:  import { useRegimeAttributionAsync } from '@/api/hooks/useRegimeAttributionAsync'
 *
 * Tech lead decision: FEP module completion + backend roadmap TD-FEP-REGIME-ASYNC.
 */
export function useRegimeAttributionParallel(
  assetRunIds: Record<string, string | null>,
  nContracts: number = 4
) {
  const entries = Object.entries(assetRunIds).filter(([, id]) => id !== null)

  return useQueries({
    queries: entries.map(([, runId]) => {
      const qs = new URLSearchParams({ n_contracts: String(nContracts) })
      return {
        queryKey: qk.regimeAttribution(runId!, nContracts),
        queryFn: (): Promise<RegimeAttributionResponse> =>
          client.get(`/api/runs/${runId}/regime-attribution?${qs}`),
        enabled: !!runId,
        staleTime: Infinity,
      }
    }),
  })
}
