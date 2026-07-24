import { cn } from '@/lib/cn'
import { useUrlState } from '@/lib/useUrlState'
import { usePortfolioRuns } from '@/api/hooks/usePortfolioRuns'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'

/** Strip poll_ + timestamp portfolio prefix when present; else bare timestamp prefix. */
function shortRunName(runId: string): string {
  return (runId ?? '')
    .replace(/^poll_\d{8}_\d{6}_portfolio_/, '')
    .replace(/^\d{8}_\d{6}_portfolio_/, '')
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
          return (
            <SelectItem
              key={run.run_id}
              value={run.run_id}
              className="[&>span:last-child]:w-full"
            >
              <div className="flex w-full items-center justify-between gap-3">
                <span className="max-w-[140px] truncate font-mono text-xs">{shortName}</span>
                <span
                  className={cn(
                    'shrink-0 font-mono text-xs',
                    run.total_return == null
                      ? 'text-text-secondary'
                      : run.total_return >= 0
                        ? 'text-gain'
                        : 'text-loss'
                  )}
                >
                  {run.total_return != null
                    ? `${run.total_return >= 0 ? '+' : ''}${(run.total_return * 100).toFixed(2)}%`
                    : '—'}
                </span>
              </div>
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}
