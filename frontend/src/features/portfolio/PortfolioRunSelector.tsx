import { cn } from '@/lib/cn'
import { percent } from '@/lib/fmt'
import { useUrlState } from '@/lib/useUrlState'
import { usePortfolioRuns } from '@/api/hooks/usePortfolioRuns'
import { usePortfolioHistory } from '@/stores/portfolioHistory'
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
  const dismissedIds = usePortfolioHistory((s) => s.dismissedIds)

  const runs = (data?.runs ?? []).filter((r) => !dismissedIds.includes(r.run_id))

  if (isLoading || isError || runs.length === 0) return null

  return (
    <Select value={runId} onValueChange={(selectedValue) => setUrlState({ run_id: selectedValue })}>
      <SelectTrigger aria-label="Select a recent portfolio run">
        <SelectValue placeholder="Select a recent run" />
      </SelectTrigger>
      <SelectContent>
        {runs.map((run) => (
          <SelectItem
            key={run.run_id}
            value={run.run_id}
            className="[&>span:first-child]:hidden [&>span:last-child]:w-full"
          >
            <div className="flex w-full items-center justify-between gap-3">
              <span className="max-w-[160px] truncate font-mono text-xs">
                {run.strategy_name ?? shortRunName(run.run_id)}
              </span>
              <span
                className={cn(
                  'shrink-0 font-mono text-xs',
                  (run.total_return ?? 0) >= 0 ? 'text-gain' : 'text-loss'
                )}
              >
                {run.total_return != null ? percent(run.total_return) : '—'}
              </span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
