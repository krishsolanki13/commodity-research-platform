import { useEffect, useState } from 'react'
import { Trash2, ClipboardCopy, Check } from 'lucide-react'
import { usePortfolioSummary } from '@/api/hooks/usePortfolioSummary'
import { usePortfolioEquity } from '@/api/hooks/usePortfolioEquity'
import { usePortfolioRisk } from '@/api/hooks/usePortfolioRisk'
import { usePortfolioCorrelation } from '@/api/hooks/usePortfolioCorrelation'
import { usePortfolioAssets } from '@/api/hooks/usePortfolioAssets'
import { usePortfolioDelete, usePortfolioRuns } from '@/api/hooks'
import { ApiClientError } from '@/api/client'
import { useUrlState } from '@/lib/useUrlState'
import { cn } from '@/lib/cn'
import { pct, dec } from '@/lib/fmt'
import { usePortfolioHistory } from '@/stores/portfolioHistory'
import { PortfolioConfigPanel } from '@/features/portfolio/PortfolioConfigPanel'
import { PortfolioLaunchPanel } from '@/features/portfolio/PortfolioLaunchPanel'
import { PortfolioKPIRow } from '@/features/portfolio/PortfolioKPIRow'
import { PortfolioEquityPanel } from '@/features/portfolio/PortfolioEquityPanel'
import { PortfolioAttributionPanel } from '@/features/portfolio/PortfolioAttributionPanel'
import { PortfolioPerAssetPanel } from '@/features/portfolio/PortfolioPerAssetPanel'
import { PortfolioRiskPanel } from '@/features/portfolio/PortfolioRiskPanel'
import { PortfolioCorrelationPanel } from '@/features/portfolio/PortfolioCorrelationPanel'
import { PortfolioRollingCorrelationPanel } from '@/features/portfolio/PortfolioRollingCorrelationPanel'
import { PortfolioRegimePanel } from '@/features/portfolio/PortfolioRegimePanel'
import { PortfolioRunSelector } from '@/features/portfolio/PortfolioRunSelector'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { Panel } from '@/ui/Panel'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/alert-dialog'

const DEFAULT_PARAMS: Record<string, Record<string, unknown>> = {
  ema_crossover: { fast_period: 50, slow_period: 200 },
  momentum: { lookback_period: 20, z_score_window: 63, signal_threshold: 0.5 },
  rsi_reversion: { period: 14, oversold_threshold: 30, overbought_threshold: 70 },
  donchian_breakout: { channel_period: 20 },
}

function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiClientError && error.apiError.status === 404
}

function shortRunId(runId: string): string {
  const clean = runId.replace(/^poll_/, '')
  return clean.length > 20 ? `${clean.slice(0, 20)}…` : clean
}

export function PortfolioAnalytics() {
  const [urlState, setUrlState] = useUrlState(portfolioUrlSchema, portfolioUrlDefaults)
  const {
    run_id,
    strategy,
    sizing_method: sizingMethod,
    initial_capital: initialCapital,
    from_date: fromDate = portfolioUrlDefaults.from_date ?? '',
    to_date: toDate = portfolioUrlDefaults.to_date ?? '',
  } = urlState

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const deleteRun = usePortfolioDelete()
  const portfolioRuns = usePortfolioRuns()
  const addRun = usePortfolioHistory((s) => s.addRun)
  const removeRun = usePortfolioHistory((s) => s.removeRun)
  const dismissedIds = usePortfolioHistory((s) => s.dismissedIds)

  const params = DEFAULT_PARAMS[strategy] ?? {}
  const cleanRunId = (run_id ?? '').replace(/^poll_/, '')
  const recentRuns = (portfolioRuns.data?.runs ?? [])
    .filter((run) => !dismissedIds.includes(run.run_id))
    .slice(0, 8)

  const summaryQuery = usePortfolioSummary(run_id ?? '')
  const summary = summaryQuery.data
  const equity = usePortfolioEquity(run_id ?? '')
  const risk = usePortfolioRisk(run_id ?? '')
  const correlation = usePortfolioCorrelation(run_id ?? '')
  const assetsQuery = usePortfolioAssets(run_id ?? '')

  const isLoading =
    summaryQuery.isLoading || equity.isLoading || risk.isLoading || correlation.isLoading

  const runMissing =
    !!run_id &&
    !summaryQuery.isLoading &&
    !equity.isLoading &&
    (isNotFoundError(summaryQuery.error) || isNotFoundError(equity.error))

  useEffect(() => {
    if (!runMissing || !run_id) return
    removeRun(run_id)
    if (cleanRunId && cleanRunId !== run_id) removeRun(cleanRunId)
  }, [runMissing, run_id, cleanRunId, removeRun])

  const deleteStrategyName =
    portfolioRuns.data?.runs.find((r) => r.run_id === deleteConfirmId)?.strategy_name ??
    summary?.strategy ??
    deleteConfirmId

  function handleConfirmDelete() {
    if (!deleteConfirmId) return
    deleteRun.mutate(deleteConfirmId, {
      onSuccess: () => {
        setDeleteConfirmId(null)
        removeRun(deleteConfirmId)
        setUrlState({ run_id: null })
      },
      onError: () => {
        setDeleteConfirmId(null)
      },
    })
  }

  function handleCopyRunId() {
    if (!cleanRunId) return
    void navigator.clipboard.writeText(cleanRunId)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function handleLaunched(id: string) {
    addRun({
      run_id: id,
      strategy,
      executed_at: new Date().toISOString(),
      n_assets: 6,
      total_return: null,
    })
    // Preserve strategy / sizing_method / initial_capital URL params.
    setUrlState({ run_id: id })
  }

  if (!run_id) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="shrink-0 px-6 pb-4 pt-6">
          <h1 className="text-xl font-semibold text-text-primary">Portfolio Analytics</h1>
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
            <Panel title="Portfolio Configuration">
              <PortfolioConfigPanel
                strategy={strategy}
                onStrategyChange={(v) => setUrlState({ strategy: v })}
                sizingMethod={sizingMethod}
                onSizingChange={(v) => setUrlState({ sizing_method: v })}
                initialCapital={initialCapital}
                onCapitalChange={(v) => setUrlState({ initial_capital: v })}
                fromDate={fromDate}
                toDate={toDate}
                onDateRangeChange={({ from, to }) =>
                  setUrlState({ from_date: from || null, to_date: to || null })
                }
              />
            </Panel>
          </div>
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
            <Panel title="Launch">
              <div className="flex flex-col gap-4">
                <PortfolioLaunchPanel
                  strategy={strategy}
                  params={params}
                  sizingMethod={sizingMethod}
                  initialCapital={initialCapital}
                  fromDate={fromDate}
                  toDate={toDate}
                  onLaunched={handleLaunched}
                />

                <div className="gap-1.5 flex flex-col">
                  <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
                    Recent Portfolio Runs
                  </span>
                  {recentRuns.length === 0 ? (
                    <p className="px-3 py-4 text-xs text-text-secondary">
                      No previous portfolio runs this session.
                    </p>
                  ) : (
                    <div className="mt-3 overflow-hidden rounded border border-border-default">
                      <table
                        role="grid"
                        aria-label="Recent portfolio runs"
                        className="w-full table-fixed border-collapse text-sm"
                      >
                        <colgroup>
                          <col className="w-[22%]" />
                          <col className="w-[24%]" />
                          <col className="w-[16%]" />
                          <col className="w-[18%]" />
                          <col className="w-[20%]" />
                        </colgroup>
                        <thead className="bg-bg-raised">
                          <tr>
                            {['RUN', 'STRATEGY', 'SHARPE', 'RETURN', 'STATUS'].map((heading) => (
                              <th
                                key={heading}
                                scope="col"
                                className="px-2 py-2 text-left text-xs font-medium text-text-secondary"
                              >
                                {heading}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {recentRuns.map((run) => {
                            const ret = run.total_return
                            const sharpe = run.sharpe
                            return (
                              <tr
                                key={run.run_id}
                                onClick={() => setUrlState({ run_id: run.run_id })}
                                className="cursor-pointer border-b border-border-default last:border-b-0 hover:bg-bg-hover"
                              >
                                <td
                                  className="truncate px-2 py-2 font-mono text-xs text-text-primary"
                                  title={run.run_id}
                                >
                                  {shortRunId(run.run_id)}
                                </td>
                                <td className="truncate px-2 py-2 text-xs text-text-secondary">
                                  {run.strategy_name}
                                </td>
                                <td className="px-2 py-2 font-mono text-xs text-text-primary">
                                  {sharpe != null ? dec(sharpe, 2) : '—'}
                                </td>
                                <td
                                  className={cn(
                                    'px-2 py-2 font-mono text-xs',
                                    ret == null
                                      ? 'text-text-secondary'
                                      : ret >= 0
                                        ? 'text-gain'
                                        : 'text-loss'
                                  )}
                                >
                                  {ret != null ? pct(ret, 1) : '—'}
                                </td>
                                <td className="px-2 py-2">
                                  <span className="flex items-center gap-1.5">
                                    <span className="h-1.5 w-1.5 rounded-full bg-gain" />
                                    <span className="font-mono text-xs text-gain">complete</span>
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    )
  }

  if (runMissing) {
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <div className="shrink-0 px-6 pb-4 pt-6">
          <h1 className="text-xl font-semibold text-text-primary">Portfolio Analytics</h1>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 py-16">
          <p className="text-sm font-medium text-text-primary">Portfolio run not found</p>
          <p className="max-w-sm text-center text-xs text-text-secondary">
            This run&apos;s data is no longer available — it may have been interrupted before
            completing. It has been removed from history.
          </p>
          <button
            type="button"
            onClick={() => setUrlState({ run_id: null })}
            className="text-xs text-text-accent hover:underline"
          >
            Return to Portfolio Analytics
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <PortfolioRunSelector />
          <div>
            <h1 className="font-mono text-base text-text-primary">Portfolio Analytics</h1>
            <div className="gap-1.5 flex items-center">
              <span className="font-mono text-xs text-text-secondary" title={cleanRunId}>
                {cleanRunId}
              </span>
              <button
                type="button"
                onClick={handleCopyRunId}
                className="ml-2 text-text-secondary transition-colors hover:text-text-primary"
                aria-label={copied ? 'Copied' : 'Copy portfolio run ID'}
                title={copied ? 'Copied' : 'Copy portfolio run ID'}
              >
                {copied ? <Check size={12} /> : <ClipboardCopy size={12} />}
              </button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => run_id && setDeleteConfirmId(run_id)}
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-loss"
            aria-label="Delete this portfolio run"
          >
            <Trash2 size={12} strokeWidth={1.75} />
            Delete run
          </button>
          <button
            onClick={() => setUrlState({ run_id: null })}
            className="text-xs text-text-accent hover:underline"
          >
            New run
          </button>
        </div>
      </div>

      <PortfolioKPIRow
        metrics={summary?.portfolio_metrics ?? null}
        loading={summaryQuery.isLoading}
      />

      <PortfolioEquityPanel
        equityData={equity.data ?? null}
        summary={summary ?? null}
        loading={equity.isLoading}
        error={equity.error}
      />

      <PortfolioAttributionPanel
        summary={summary ?? null}
        correlation={correlation.data ?? null}
        assetsData={assetsQuery.data ?? null}
        assetsLoading={assetsQuery.isLoading}
        loading={isLoading}
      />

      <PortfolioPerAssetPanel runId={run_id} assets={summary?.assets ?? []} />

      <PortfolioRiskPanel risk={risk.data ?? null} loading={risk.isLoading} />

      <PortfolioCorrelationPanel
        correlation={correlation.data ?? null}
        loading={correlation.isLoading}
        error={correlation.error}
      />

      {correlation.data && (
        <PortfolioRollingCorrelationPanel
          correlation={correlation.data}
          loading={correlation.isLoading}
        />
      )}

      <section>
        <div className="mb-3">
          <span className="font-mono text-sm">Regime Attribution</span>
        </div>
        <PortfolioRegimePanel runId={run_id} assetRunIds={assetsQuery.data?.asset_run_ids} />
      </section>

      <AlertDialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this portfolio run?</AlertDialogTitle>
            <AlertDialogDescription>
              Strategy <span className="font-mono text-text-emphasis">{deleteStrategyName}</span>{' '}
              will be permanently deleted. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              style={{ backgroundColor: 'var(--text-loss)', color: 'white' }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default PortfolioAnalytics
