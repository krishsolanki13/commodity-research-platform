/**
 * BacktestConfigPanel — cost/sizing configuration form.
 * Calls onChange on every user-initiated change (not on mount).
 */
import { useState } from 'react'
import { ParamForm } from '@/components/inputs/ParamForm'
import { Panel } from '@/ui/Panel'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type ParamSpec = components['schemas']['ParamSpec']

export interface BacktestConfig {
  initial_capital: number
  commission_per_trade: number
  slippage_ticks: number
  sizing_method: 'fixed_notional' | 'volatility_scaled'
  notional_usd: number
  signal_threshold: number
}

const BACKTEST_CONFIG_SCHEMA: ParamSpec[] = [
  {
    name: 'initial_capital',
    kind: 'float',
    default: 1000000,
    min: 1000,
    max: 100000000,
    description: 'Initial capital',
    unit: 'USD',
  },
  {
    name: 'commission_per_trade',
    kind: 'float',
    default: 5.0,
    min: 0,
    max: 100,
    description: 'Commission per trade',
    unit: 'USD',
  },
  {
    name: 'slippage_ticks',
    kind: 'int',
    default: 1,
    min: 0,
    max: 10,
    description: 'Slippage',
    unit: 'ticks',
  },
  {
    name: 'notional_usd',
    kind: 'float',
    default: 100000,
    min: 10000,
    max: 10000000,
    description: 'Notional per signal (fixed sizing)',
    unit: 'USD',
  },
  {
    name: 'signal_threshold',
    kind: 'float',
    default: 0.0,
    min: -1.0,
    max: 1.0,
    description: 'Signal threshold',
  },
]

const DEFAULT_CONFIG: BacktestConfig = {
  initial_capital: 1_000_000,
  commission_per_trade: 5.0,
  slippage_ticks: 1,
  sizing_method: 'fixed_notional',
  notional_usd: 100_000,
  signal_threshold: 0.0,
}

interface BacktestConfigPanelProps {
  asset: string
  strategy: string
  params: Record<string, unknown>
  onChange: (config: BacktestConfig) => void
  className?: string
}

export function BacktestConfigPanel({
  asset,
  strategy,
  params,
  onChange,
  className,
}: BacktestConfigPanelProps) {
  const [config, setConfig] = useState<BacktestConfig>(DEFAULT_CONFIG)

  function updateConfig(next: BacktestConfig) {
    setConfig(next)
    onChange(next)
  }

  function handleSizingMethod(method: BacktestConfig['sizing_method']) {
    updateConfig({ ...config, sizing_method: method })
  }

  function handleParamChange(values: Record<string, unknown>) {
    updateConfig({
      ...config,
      initial_capital: Number(values.initial_capital ?? config.initial_capital),
      commission_per_trade: Number(values.commission_per_trade ?? config.commission_per_trade),
      slippage_ticks: Number(values.slippage_ticks ?? config.slippage_ticks),
      notional_usd: Number(values.notional_usd ?? config.notional_usd),
      signal_threshold: Number(values.signal_threshold ?? config.signal_threshold),
    })
  }

  const visibleSchema =
    config.sizing_method === 'volatility_scaled'
      ? BACKTEST_CONFIG_SCHEMA.filter((s) => s.name !== 'notional_usd')
      : BACKTEST_CONFIG_SCHEMA

  const formValues: Record<string, unknown> = {
    initial_capital: config.initial_capital,
    commission_per_trade: config.commission_per_trade,
    slippage_ticks: config.slippage_ticks,
    signal_threshold: config.signal_threshold,
  }
  if (config.sizing_method === 'fixed_notional') {
    formValues.notional_usd = config.notional_usd
  }

  const hasPeriods = params.fast_period != null && params.slow_period != null

  return (
    <Panel title="Backtest Config" className={className}>
      <div className="flex flex-col gap-4">
        <p className="font-mono text-xs text-text-secondary">
          {[
            asset && asset.toUpperCase(),
            strategy,
            hasPeriods ? `${String(params.fast_period)}/${String(params.slow_period)}` : null,
          ]
            .filter(Boolean)
            .join(' · ') || 'Select an asset and strategy'}
        </p>

        <div className="flex overflow-hidden rounded-sm border border-border-strong">
          <button
            type="button"
            aria-pressed={config.sizing_method === 'fixed_notional'}
            onClick={() => handleSizingMethod('fixed_notional')}
            className={cn(
              'border-r border-border-strong px-2 py-1 font-mono text-xs last:border-r-0',
              'transition-colors duration-fast',
              config.sizing_method === 'fixed_notional'
                ? 'bg-accent font-medium text-bg-app'
                : 'bg-bg-app text-text-secondary hover:bg-bg-hover hover:text-text-primary'
            )}
          >
            Fixed Notional
          </button>
          <button
            type="button"
            aria-pressed={config.sizing_method === 'volatility_scaled'}
            onClick={() => handleSizingMethod('volatility_scaled')}
            className={cn(
              'border-r border-border-strong px-2 py-1 font-mono text-xs last:border-r-0',
              'transition-colors duration-fast',
              config.sizing_method === 'volatility_scaled'
                ? 'bg-accent font-medium text-bg-app'
                : 'bg-bg-app text-text-secondary hover:bg-bg-hover hover:text-text-primary'
            )}
          >
            Volatility Scaled
          </button>
        </div>

        <ParamForm schema={visibleSchema} values={formValues} onChange={handleParamChange} />
      </div>
    </Panel>
  )
}
