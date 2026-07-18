import { useState } from 'react'
import { usePortfolioSummary } from '@/api/hooks/usePortfolioSummary'
import { usePortfolioEquity } from '@/api/hooks/usePortfolioEquity'
import { usePortfolioRisk } from '@/api/hooks/usePortfolioRisk'
import { usePortfolioCorrelation } from '@/api/hooks/usePortfolioCorrelation'
import { PortfolioConfigPanel } from '@/features/portfolio/PortfolioConfigPanel'
import { PortfolioLaunchPanel } from '@/features/portfolio/PortfolioLaunchPanel'
import { PortfolioKPIRow } from '@/features/portfolio/PortfolioKPIRow'
import { PortfolioEquityPanel } from '@/features/portfolio/PortfolioEquityPanel'
import { PortfolioAttributionPanel } from '@/features/portfolio/PortfolioAttributionPanel'
import { PortfolioRiskPanel } from '@/features/portfolio/PortfolioRiskPanel'
import { PortfolioCorrelationPanel } from '@/features/portfolio/PortfolioCorrelationPanel'
import { EmptyState } from '@/components/layout/EmptyState'

const STRATEGIES = [
  'ema_crossover',
  'momentum',
  'rsi_reversion',
  'donchian_breakout',
]

const DEFAULT_PARAMS: Record<string, Record<string, unknown>> = {
  ema_crossover: { fast_period: 50, slow_period: 200 },
  momentum: { lookback_period: 20, z_score_window: 63, signal_threshold: 0.5 },
  rsi_reversion: { period: 14, oversold_threshold: 30, overbought_threshold: 70 },
  donchian_breakout: { channel_period: 20 },
}

export function PortfolioAnalytics() {
  const [runId, setRunId] = useState<string | undefined>(undefined)
  const [strategy, setStrategy] = useState('ema_crossover')
  const [sizingMethod, setSizingMethod] = useState<'fixed_notional' | 'volatility_scaled'>(
    'fixed_notional'
  )
  const [initialCapital, setInitialCapital] = useState(1_000_000)

  const params = DEFAULT_PARAMS[strategy] ?? {}

  const summary = usePortfolioSummary(runId ?? '')
  const equity = usePortfolioEquity(runId ?? '')
  const risk = usePortfolioRisk(runId ?? '')
  const correlation = usePortfolioCorrelation(runId ?? '')

  const isLoading =
    summary.isLoading ||
    equity.isLoading ||
    risk.isLoading ||
    correlation.isLoading

  if (!runId) {
    return (
      <div className="flex gap-6 p-6">
        <div className="w-80 shrink-0 flex flex-col gap-4">
          <p className="text-sm font-mono text-text-secondary uppercase">
            Portfolio Configuration
          </p>
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
        <div className="flex-1 flex flex-col gap-4">
          <PortfolioLaunchPanel
            strategy={strategy}
            params={params}
            sizingMethod={sizingMethod}
            initialCapital={initialCapital}
            onLaunched={(id) => setRunId(id)}
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
        <div>
          <h1 className="text-base font-mono text-text-primary">
            Portfolio Analytics
          </h1>
          <span className="text-xs font-mono text-text-secondary">{runId}</span>
        </div>
        <button
          onClick={() => setRunId(undefined)}
          className="text-xs font-mono text-text-secondary hover:text-text-primary border border-border-default px-3 py-1 rounded"
        >
          ← New run
        </button>
      </div>

      <PortfolioKPIRow
        metrics={summary.data?.portfolio_metrics ?? null}
        loading={summary.isLoading}
      />

      <PortfolioEquityPanel
        equityData={equity.data ?? null}
        summary={summary.data ?? null}
        loading={equity.isLoading}
        error={equity.error}
      />

      <PortfolioAttributionPanel
        summary={summary.data ?? null}
        correlation={correlation.data ?? null}
        loading={isLoading}
      />

      <PortfolioRiskPanel
        risk={risk.data ?? null}
        loading={risk.isLoading}
      />

      <PortfolioCorrelationPanel
        correlation={correlation.data ?? null}
        loading={correlation.isLoading}
      />
    </div>
  )
}

export default PortfolioAnalytics
