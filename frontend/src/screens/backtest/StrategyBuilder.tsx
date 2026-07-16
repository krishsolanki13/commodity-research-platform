/**
 * StrategyBuilder (S4) — configure and launch a backtest from URL context.
 * Reads F5 signal-evaluate cache only (useSignalEvaluate has enabled: false).
 */
import { useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useSignalEvaluate } from '@/api/hooks'
import { EvalSummaryCard } from '@/features/backtest/EvalSummaryCard'
import { BacktestConfigPanel } from '@/features/backtest/BacktestConfigPanel'
import type { BacktestConfig } from '@/features/backtest/BacktestConfigPanel'
import { LaunchPanel } from '@/features/backtest/LaunchPanel'
import { safeJsonParse } from '@/lib/json'
import type { components } from '@/api/schema'

type BacktestLaunchRequest = components['schemas']['BacktestLaunchRequest']

export default function StrategyBuilder() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const asset = searchParams.get('asset') ?? ''
  const strategy = searchParams.get('strategy') ?? ''
  const paramsJson = searchParams.get('params') ?? '{}'
  const evalOverride = searchParams.get('evalOverride') === '1'
  const parsedParams = safeJsonParse<Record<string, unknown>>(paramsJson, {})

  // Cache-read only — useSignalEvaluate never auto-fetches (enabled: false internally)
  const cachedEval = useSignalEvaluate(asset, strategy, parsedParams)
  const evaluation = evalOverride ? null : (cachedEval.data?.evaluation ?? null)

  const [config, setConfig] = useState<BacktestConfig>({
    initial_capital: 1_000_000,
    commission_per_trade: 5.0,
    slippage_ticks: 1,
    sizing_method: 'fixed_notional',
    notional_usd: 100_000,
    signal_threshold: 0.0,
  })

  // signal_evaluation: null when evalOverride — records IC Gate override in run metadata
  const launchRequest: BacktestLaunchRequest = {
    asset,
    strategy,
    params: parsedParams,
    initial_capital: config.initial_capital,
    commission_per_trade: config.commission_per_trade,
    slippage_ticks: config.slippage_ticks,
    sizing_method: config.sizing_method,
    notional_usd: config.notional_usd,
    signal_threshold: config.signal_threshold,
    signal_evaluation: evalOverride ? null : evaluation,
  }

  function handleLaunched(runId: string) {
    void navigate(`/runs/${runId}`)
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="mb-2">
        <nav className="mb-1 text-xs text-text-secondary">
          <Link to="/market">Market</Link>
          {' / '}
          <Link to={`/market/${asset}`}>{asset.toUpperCase()}</Link>
          {' / Strategy Builder'}
        </nav>
        <h1 className="text-xl font-semibold text-text-primary">Strategy Builder</h1>
      </div>

      <div className="flex gap-6">
        <div className="w-96 flex shrink-0 flex-col gap-4">
          <EvalSummaryCard
            evaluation={evaluation}
            evalOverride={evalOverride}
            asset={asset}
            strategy={strategy}
          />
          <BacktestConfigPanel
            asset={asset}
            strategy={strategy}
            params={parsedParams}
            onChange={setConfig}
          />
        </div>
        <div className="flex-1">
          <LaunchPanel
            config={config}
            evalSummary={evaluation}
            evalOverride={evalOverride}
            launchRequest={launchRequest}
            onLaunched={handleLaunched}
          />
        </div>
      </div>
    </div>
  )
}
