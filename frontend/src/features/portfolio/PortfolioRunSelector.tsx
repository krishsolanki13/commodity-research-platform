import { fmt } from '@/lib/fmt'
import { useUrlState } from '@/lib/useUrlState'
import { usePortfolioRuns } from '@/api/hooks/usePortfolioRuns'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'

function truncateRunId(runId: string): string {
  return runId.length > 18 ? `…${runId.slice(-18)}` : runId
}

export function PortfolioRunSelector() {
  const { data, isLoading, isError } = usePortfolioRuns()
  const [{ run_id: runId }, setUrlState] = useUrlState(portfolioUrlSchema, portfolioUrlDefaults)

  const runs = data?.runs ?? []

  if (isLoading || isError || runs.length === 0) return null

  return (
    <Select value={runId} onValueChange={(selectedValue) => setUrlState({ run_id: selectedValue })}>
      <SelectTrigger aria-label="Select a recent portfolio run">
        <SelectValue placeholder="Select a recent run" />
      </SelectTrigger>
      <SelectContent>
        {runs.map((run) => (
          <SelectItem key={run.run_id} value={run.run_id}>
            <span className="flex items-center gap-2">
              <span>{truncateRunId(run.run_id)}</span>
              <span>{run.strategy_name}</span>
              <span
                className={
                  run.total_return == null
                    ? 'text-text-secondary'
                    : run.total_return < 0
                      ? 'text-loss'
                      : 'text-gain'
                }
              >
                {run.total_return == null ? '—' : fmt.percent(run.total_return)}
              </span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
