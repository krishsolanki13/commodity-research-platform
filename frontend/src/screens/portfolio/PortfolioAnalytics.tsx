import { useState } from 'react'
import { Trash2, ClipboardCopy, Check } from 'lucide-react'
import { usePortfolioSummary } from '@/api/hooks/usePortfolioSummary'
import { usePortfolioEquity } from '@/api/hooks/usePortfolioEquity'
import { usePortfolioRisk } from '@/api/hooks/usePortfolioRisk'
import { usePortfolioCorrelation } from '@/api/hooks/usePortfolioCorrelation'
import { usePortfolioAssets } from '@/api/hooks/usePortfolioAssets'
import { usePortfolioDelete, usePortfolioRuns } from '@/api/hooks'
import { useUrlState } from '@/lib/useUrlState'
import { PortfolioConfigPanel } from '@/features/portfolio/PortfolioConfigPanel'
import { PortfolioLaunchPanel } from '@/features/portfolio/PortfolioLaunchPanel'
import { PortfolioKPIRow } from '@/features/portfolio/PortfolioKPIRow'
import { PortfolioEquityPanel } from '@/features/portfolio/PortfolioEquityPanel'
import { PortfolioAttributionPanel } from '@/features/portfolio/PortfolioAttributionPanel'
import { PortfolioPerAssetPanel } from '@/features/portfolio/PortfolioPerAssetPanel'
import { PortfolioRiskPanel } from '@/features/portfolio/PortfolioRiskPanel'
import { PortfolioCorrelationPanel } from '@/features/portfolio/PortfolioCorrelationPanel'
import { PortfolioRollingCorrelationPanel } from '@/features/portfolio/PortfolioRollingCorrelationPanel'
import { PortfolioRunSelector } from '@/features/portfolio/PortfolioRunSelector'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { EmptyState } from '@/components/layout/EmptyState'
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

export function PortfolioAnalytics() {
  const [{ run_id }, setUrlState] = useUrlState(portfolioUrlSchema, portfolioUrlDefaults)
  const [strategy, setStrategy] = useState('ema_crossover')
  const [sizingMethod, setSizingMethod] = useState<'fixed_notional' | 'volatility_scaled'>(
    'fixed_notional'
  )
  const [initialCapital, setInitialCapital] = useState(1_000_000)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const deleteRun = usePortfolioDelete()
  const portfolioRuns = usePortfolioRuns()

  const params = DEFAULT_PARAMS[strategy] ?? {}
  const cleanRunId = (run_id ?? '').replace(/^poll_/, '')

  const summaryQuery = usePortfolioSummary(run_id ?? '')
  const summary = summaryQuery.data
  const equity = usePortfolioEquity(run_id ?? '')
  const risk = usePortfolioRisk(run_id ?? '')
  const correlation = usePortfolioCorrelation(run_id ?? '')
  const assetsQuery = usePortfolioAssets(run_id ?? '')

  const isLoading =
    summaryQuery.isLoading || equity.isLoading || risk.isLoading || correlation.isLoading

  const deleteStrategyName =
    portfolioRuns.data?.runs.find((r) => r.run_id === deleteConfirmId)?.strategy_name ??
    summary?.strategy ??
    deleteConfirmId

  function handleConfirmDelete() {
    if (!deleteConfirmId) return
    deleteRun.mutate(deleteConfirmId, {
      onSuccess: () => {
        setDeleteConfirmId(null)
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

  if (!run_id) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="shrink-0 px-6 pt-6 pb-4">
          <h1 className="text-xl font-semibold text-text-primary">Portfolio Analytics</h1>
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
            <Panel title="Portfolio Configuration">
              <PortfolioConfigPanel
                strategy={strategy}
                onStrategyChange={setStrategy}
                sizingMethod={sizingMethod}
                onSizingChange={setSizingMethod}
                initialCapital={initialCapital}
                onCapitalChange={setInitialCapital}
              />
            </Panel>
          </div>
          <div className="flex min-h-0 flex-col gap-4">
            <Panel title="Launch">
              <PortfolioLaunchPanel
                strategy={strategy}
                params={params}
                sizingMethod={sizingMethod}
                initialCapital={initialCapital}
                onLaunched={(id) => setUrlState({ run_id: id })}
              />
            </Panel>
            <EmptyState
              title="No portfolio run selected"
              body="Launch a portfolio backtest to see analytics."
              className="h-48 rounded border border-border-default bg-bg-raised"
            />
          </div>
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
      />

      {correlation.data && (
        <PortfolioRollingCorrelationPanel
          correlation={correlation.data}
          loading={correlation.isLoading}
        />
      )}

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
