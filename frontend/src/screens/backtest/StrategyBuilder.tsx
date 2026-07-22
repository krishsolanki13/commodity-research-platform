/**
 * StrategyBuilder (S4) — configure and launch a backtest from URL context.
 * Prefers URL-threaded `evaluation` (Issue T); falls back to F5 evaluate-chain cache.
 * Asset/strategy selectors are always visible for direct /backtest/new navigation.
 */
import { useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useAssets, useStrategies, useSignalEvaluate } from '@/api/hooks'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { StrategyPicker } from '@/components/inputs/StrategyPicker'
import { ParamForm } from '@/components/inputs/ParamForm'
import { EvalSummaryCard } from '@/features/backtest/EvalSummaryCard'
import { BacktestConfigPanel } from '@/features/backtest/BacktestConfigPanel'
import type { BacktestConfig } from '@/features/backtest/BacktestConfigPanel'
import { LaunchPanel } from '@/features/backtest/LaunchPanel'
import { Panel } from '@/ui/Panel'
import { safeJsonParse } from '@/lib/json'
import type { components } from '@/api/schema'

type BacktestLaunchRequest = components['schemas']['BacktestLaunchRequest']

export default function StrategyBuilder() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const asset = searchParams.get('asset') ?? ''
  const strategy = searchParams.get('strategy') ?? ''
  const paramsJson = searchParams.get('params') ?? '{}'
  const evaluationJson = searchParams.get('evaluation')
  const evalOverride = searchParams.get('evalOverride') === '1'
  const parsedParams = safeJsonParse<Record<string, unknown>>(paramsJson, {})

  type SignalEvaluationData = components['schemas']['SignalEvaluationData']
  const urlEvaluation = evaluationJson
    ? safeJsonParse<SignalEvaluationData | null>(evaluationJson, null)
    : null

  const { data: assetsData } = useAssets()
  const { data: strategiesData } = useStrategies()
  const strategies = strategiesData?.strategies ?? []
  const selectedStrategy = strategies.find((s) => s.name === strategy)

  // Prefer URL-threaded evaluation (Issue T); fall back to F5 evaluate-chain cache
  const cachedEval = useSignalEvaluate(asset, strategy, parsedParams)
  const evaluation = evalOverride ? null : (urlEvaluation ?? cachedEval.data?.evaluation ?? null)

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

  function patchParams(patch: Record<string, string | null>) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [key, value] of Object.entries(patch)) {
          if (value === null || value === '') next.delete(key)
          else next.set(key, value)
        }
        return next
      },
      { replace: true }
    )
  }

  function handleAssetChange(nextAsset: string) {
    patchParams({ asset: nextAsset })
  }

  function handleStrategyChange(nextStrategy: string) {
    const meta = strategies.find((s) => s.name === nextStrategy)
    const defaultParams = (meta?.default_params ?? {}) as Record<string, unknown>
    patchParams({
      strategy: nextStrategy,
      params: JSON.stringify(defaultParams),
    })
  }

  function handleLaunched(runId: string) {
    void navigate(`/runs/${runId}`)
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="mb-2">
        <nav className="mb-1 text-xs text-text-secondary">
          <Link to="/market">Market</Link>
          {asset ? (
            <>
              {' / '}
              <Link to={`/market/${asset}`}>{asset.toUpperCase()}</Link>
            </>
          ) : null}
          {' / Strategy Builder'}
        </nav>
        <h1 className="text-xl font-semibold text-text-primary">Strategy Builder</h1>
      </div>

      <div className="flex gap-6">
        <div className="w-96 flex shrink-0 flex-col gap-4">
          <Panel title="Strategy">
            <div className="flex flex-col gap-4">
              <AssetSelector
                value={asset || null}
                onChange={handleAssetChange}
                assets={assetsData?.assets ?? []}
                aria-label="Select asset"
              />
              <StrategyPicker
                strategies={strategies}
                value={strategy || null}
                onChange={handleStrategyChange}
              />
              {strategy && (selectedStrategy?.params_schema?.length ?? 0) > 0 && (
                <ParamForm
                  schema={selectedStrategy?.params_schema ?? []}
                  values={parsedParams}
                  onChange={(newParams) => patchParams({ params: JSON.stringify(newParams) })}
                />
              )}
            </div>
          </Panel>

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
