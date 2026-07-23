import { fmt } from '@/lib/fmt'
import { useUrlState } from '@/lib/useUrlState'
import { usePortfolioRuns } from '@/api/hooks/usePortfolioRuns'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'

function shortRunName(runId: string): string {
  return (runId ?? '').replace(/^poll_/, '').replace(/^\d{8}_\d{6}_portfolio_/, '')
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
        {runs.map((run) => {
          const shortName = shortRunName(run.run_id) || run.strategy_name
          const returnPct = run.total_return == null ? '—' : fmt.percent(run.total_return)
          return (
            <SelectItem key={run.run_id} value={run.run_id}>
              <div className="flex w-full items-center justify-between gap-4">
                <span>{shortName}</span>
                <span
                  className={
                    run.total_return == null
                      ? 'text-xs text-text-secondary'
                      : run.total_return < 0
                        ? 'text-xs text-loss'
                        : 'text-xs text-gain'
                  }
                >
                  {returnPct}
                </span>
              </div>
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}
