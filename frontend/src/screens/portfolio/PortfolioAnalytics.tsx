import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { usePortfolioSummary } from '@/api/hooks/usePortfolioSummary'
import { usePortfolioEquity } from '@/api/hooks/usePortfolioEquity'
import { usePortfolioRisk } from '@/api/hooks/usePortfolioRisk'
import { usePortfolioCorrelation } from '@/api/hooks/usePortfolioCorrelation'
import { usePortfolioDelete } from '@/api/hooks'
import { useUrlState } from '@/lib/useUrlState'
import { usePortfolioHistory } from '@/stores/portfolioHistory'
import { PortfolioConfigPanel } from '@/features/portfolio/PortfolioConfigPanel'
import { PortfolioLaunchPanel } from '@/features/portfolio/PortfolioLaunchPanel'
import { PortfolioKPIRow } from '@/features/portfolio/PortfolioKPIRow'
import { PortfolioEquityPanel } from '@/features/portfolio/PortfolioEquityPanel'
import { PortfolioAttributionPanel } from '@/features/portfolio/PortfolioAttributionPanel'
import { PortfolioPerAssetPanel } from '@/features/portfolio/PortfolioPerAssetPanel'
import { PortfolioRiskPanel } from '@/features/portfolio/PortfolioRiskPanel'
import { PortfolioCorrelationPanel } from '@/features/portfolio/PortfolioCorrelationPanel'
import { PortfolioRunSelector } from '@/features/portfolio/PortfolioRunSelector'
import { portfolioUrlDefaults, portfolioUrlSchema } from '@/features/portfolio/portfolioUrlState'
import { EmptyState } from '@/components/layout/EmptyState'
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

const STRATEGIES = ['ema_crossover', 'momentum', 'rsi_reversion', 'donchian_breakout']

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
  const history = usePortfolioHistory()
  const deleteRun = usePortfolioDelete()

  const params = DEFAULT_PARAMS[strategy] ?? {}

  const summaryQuery = usePortfolioSummary(run_id ?? '')
  const summary = summaryQuery.data
  const equity = usePortfolioEquity(run_id ?? '')
  const risk = usePortfolioRisk(run_id ?? '')
  const correlation = usePortfolioCorrelation(run_id ?? '')

  const isLoading =
    summaryQuery.isLoading || equity.isLoading || risk.isLoading || correlation.isLoading

  useEffect(() => {
    if (!summary || !run_id || history.has(run_id)) return
    history.addRun({
      run_id,
      strategy: summary.strategy,
      executed_at: new Date().toISOString(),
      n_assets: summary.assets?.length ?? 0,
      total_return: summary.portfolio_metrics?.total_return ?? null,
    })
    // The run ID and loaded summary are the only recording triggers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary?.run_id, run_id])

  function handleConfirmDelete() {
    if (!deleteConfirmId) return
    deleteRun.mutate(deleteConfirmId, {
      onSuccess: () => {
        history.removeRun(deleteConfirmId)
        setDeleteConfirmId(null)
        setUrlState({ run_id: undefined })
      },
      onError: () => {
        setDeleteConfirmId(null)
      },
    })
  }

  if (!run_id) {
    return (
      <div className="flex gap-6 p-6">
        <div className="w-80 flex shrink-0 flex-col gap-4">
          <p className="font-mono text-sm uppercase text-text-secondary">Portfolio Configuration</p>
          <PortfolioConfigPanel
            strategy={strategy}
            onStrategyChange={setStrategy}
            sizingMethod={sizingMethod}
            onSizingChange={setSizingMethod}
            initialCapital={initialCapital}
            onCapitalChange={setInitialCapital}
            strategies={STRATEGIES}
          />
        </div>
        <div className="flex flex-1 flex-col gap-4">
          <PortfolioLaunchPanel
            strategy={strategy}
            params={params}
            sizingMethod={sizingMethod}
            initialCapital={initialCapital}
            onLaunched={(id) => setUrlState({ run_id: id })}
          />
          <EmptyState
            title="No portfolio run selected"
            body="Launch a portfolio backtest to see analytics."
            className="h-48 rounded border border-border-default bg-bg-raised"
          />
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
            <span className="block max-w-xs truncate font-mono text-xs text-text-secondary">
              {run_id}
            </span>
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
            onClick={() => setUrlState({ run_id: undefined })}
            className="text-xs text-text-accent hover:underline"
          >
            ← New run
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
        loading={isLoading}
      />

      <PortfolioPerAssetPanel runId={run_id} assets={summary?.assets ?? []} />

      <PortfolioRiskPanel risk={risk.data ?? null} loading={risk.isLoading} />

      <PortfolioCorrelationPanel
        correlation={correlation.data ?? null}
        loading={correlation.isLoading}
      />

      <AlertDialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => !open && setDeleteConfirmId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this portfolio run?</AlertDialogTitle>
            <AlertDialogDescription>
              Run{' '}
              <span className="font-mono text-text-emphasis">{deleteConfirmId?.slice(-20)}</span>{' '}
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
