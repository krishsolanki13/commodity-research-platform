import { useEffect, useMemo } from 'react'
import { z } from 'zod'
import { useUrlState } from '@/lib/useUrlState'
import { safeJsonParse } from '@/lib/json'
import { useAssets } from '@/api/hooks/useAssets'
import { useIndicators } from '@/api/hooks/useIndicators'
import { useStrategies } from '@/api/hooks/useStrategies'
import { AssetSelector } from '@/components/inputs/AssetSelector'
import { DateRangePicker } from '@/components/inputs/DateRangePicker'
import { StrategyPicker } from '@/components/inputs/StrategyPicker'
import { IndicatorPicker } from '@/components/inputs/IndicatorPicker'
import { ParamForm } from '@/components/inputs/ParamForm'
import { Panel } from '@/ui/Panel'
import type { components } from '@/api/schema'

type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']

const workbenchSchema = z.object({
  asset: z.string().optional(),
  strategy: z.string().optional(),
  params: z.string().optional(),
  features: z.string().optional(),
  from_date: z.string().optional(),
  to_date: z.string().optional(),
})

const defaults = {
  asset: undefined as string | undefined,
  strategy: undefined as string | undefined,
  params: undefined as string | undefined,
  features: undefined as string | undefined,
  from_date: '2015-01-01',
  to_date: new Date().toISOString().slice(0, 10),
}

export interface EvaluateParams {
  asset: string
  strategy: string
  params: Record<string, unknown>
  featureSpecs: FeatureSpecRequest[]
  fromDate: string
  toDate: string
}

export interface EvaluateProgress {
  step: 'features' | 'signal' | 'evaluation'
  stepIndex: 1 | 2 | 3
}

interface WorkbenchConfigRailProps {
  onEvaluate: (params: EvaluateParams) => void
  onCanEvaluateChange: (canEvaluate: boolean, reason: string | null) => void
  onEvaluateReady?: (trigger: () => void) => void
}

/** Maps strategy + params → feature specs required by the signal. Uses live API indicator names. */
export function getRequiredFeatureSpecs(
  strategy: string,
  params: Record<string, unknown>
): FeatureSpecRequest[] {
  switch (strategy) {
    case 'ema_crossover':
      return [
        { name: 'ema', params: { period: Number(params.fast_period ?? 50) } },
        { name: 'ema', params: { period: Number(params.slow_period ?? 200) } },
      ]
    case 'momentum':
      // momentum indicator uses 'lookback'; strategy param is 'lookback_period'
      return [{ name: 'momentum', params: { lookback: Number(params.lookback_period ?? 20) } }]
    case 'rsi_reversion':
      return [{ name: 'rsi', params: { period: Number(params.period ?? 14) } }]
    case 'donchian_breakout':
      return [] // Q4: computes from OHLCV directly; no feature column required
    default:
      return []
  }
}

function specsMatch(a: FeatureSpecRequest, b: FeatureSpecRequest): boolean {
  return a.name === b.name && JSON.stringify(a.params) === JSON.stringify(b.params)
}

export function WorkbenchConfigRail({
  onEvaluate,
  onCanEvaluateChange,
  onEvaluateReady,
}: WorkbenchConfigRailProps) {
  const [urlState, setUrlState] = useUrlState(workbenchSchema, defaults)

  const { data: assetsData } = useAssets()
  const { data: indicatorsData } = useIndicators()
  const { data: strategiesData } = useStrategies()

  const assets = assetsData?.assets
  const indicators = indicatorsData?.indicators
  const strategies = strategiesData?.strategies

  const strategy = urlState.strategy
  const parsedParams = safeJsonParse<Record<string, unknown>>(urlState.params, {})
  const parsedFeatures = safeJsonParse<FeatureSpecRequest[]>(urlState.features, [])

  const selectedStrategy = strategies?.find((s) => s.name === strategy)

  const requiredSpecs = useMemo(
    () => (strategy ? getRequiredFeatureSpecs(strategy, parsedParams) : []),
    // parsedParams identity changes every render — key off the URL string
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [strategy, urlState.params]
  )
  const allRequiredPresent = requiredSpecs.every((req) =>
    parsedFeatures.some((f) => specsMatch(f, req))
  )
  const missingSpecs = requiredSpecs.filter(
    (req) => !parsedFeatures.some((f) => specsMatch(f, req))
  )
  const firstMissing = missingSpecs[0]
  const missingLabel = (() => {
    if (!firstMissing) return null
    const raw = Object.values(firstMissing.params ?? {})[0]
    const suffix =
      typeof raw === 'string' || typeof raw === 'number' || typeof raw === 'boolean'
        ? String(raw)
        : ''
    return `${firstMissing.name}_${suffix}`
  })()

  const canEvaluate = !!urlState.asset && !!strategy && allRequiredPresent
  const evaluateDisabledReason = !urlState.asset
    ? 'Select an asset'
    : !strategy
      ? 'Select a strategy'
      : !allRequiredPresent && missingLabel
        ? `Add ${missingLabel} to evaluate this signal`
        : null

  // Notify parent whenever evaluate readiness changes
  useEffect(() => {
    onCanEvaluateChange(canEvaluate, evaluateDisabledReason)
  }, [canEvaluate, evaluateDisabledReason, onCanEvaluateChange])

  // Sync required feature specs into URL when strategy/params imply missing ones
  // (shareable URLs may omit features; strategy change handler also writes them).
  useEffect(() => {
    if (!strategy || requiredSpecs.length === 0) return
    if (allRequiredPresent) return
    const merged = [...parsedFeatures]
    for (const req of requiredSpecs) {
      if (!merged.some((f) => specsMatch(f, req))) merged.push(req)
    }
    setUrlState({ features: JSON.stringify(merged) })
    // Intentionally keyed off URL strings + strategy, not array identities
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy, urlState.params, urlState.features, allRequiredPresent, setUrlState])

  function handleStrategyChange(newStrategy: string) {
    const meta = strategies?.find((s) => s.name === newStrategy)
    const defaultParams = (meta?.default_params ?? {}) as Record<string, unknown>
    const required = getRequiredFeatureSpecs(newStrategy, defaultParams)
    setUrlState({
      strategy: newStrategy,
      params: JSON.stringify(defaultParams),
      features: JSON.stringify(required),
    })
  }

  function handleEvaluateClick() {
    if (!urlState.asset || !strategy) return
    onEvaluate({
      asset: urlState.asset,
      strategy,
      params: parsedParams,
      featureSpecs: parsedFeatures,
      fromDate: urlState.from_date ?? defaults.from_date,
      toDate: urlState.to_date ?? defaults.to_date,
    })
  }

  // Register the evaluate trigger with the parent so the button in ResearchWorkbench
  // can call handleEvaluateClick without duplicating param-building logic here.
  useEffect(() => {
    onEvaluateReady?.(() => handleEvaluateClick())
    // Re-register whenever params change so the trigger captures fresh state
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canEvaluate, urlState])

  const fromDate = urlState.from_date ?? defaults.from_date
  const toDate = urlState.to_date ?? defaults.to_date

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Asset & Strategy">
        <div className="flex flex-col gap-4">
          <AssetSelector
            value={urlState.asset ?? null}
            onChange={(asset) => setUrlState({ asset })}
            assets={assets ?? []}
            aria-label="Select asset"
          />
          <DateRangePicker
            value={{ from: fromDate, to: toDate }}
            onChange={({ from, to }) =>
              setUrlState({ from_date: from, to_date: to })}
          />
          <StrategyPicker
            strategies={strategies ?? []}
            value={strategy ?? null}
            onChange={handleStrategyChange}
          />
          {strategy && (
            <ParamForm
              schema={selectedStrategy?.params_schema ?? []}
              values={parsedParams}
              onChange={(newParams) =>
                setUrlState({ params: JSON.stringify(newParams) })}
            />
          )}
        </div>
      </Panel>

      <Panel title="Indicators">
        <IndicatorPicker
          catalog={indicators ?? []}
          selected={parsedFeatures}
          onChange={(newSpecs) =>
            setUrlState({ features: JSON.stringify(newSpecs) })}
          requiredSpecs={requiredSpecs}
        />
      </Panel>
    </div>
  )
}
