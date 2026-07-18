import { fmt } from '@/lib/fmt'

interface PortfolioConfigPanelProps {
  strategy: string
  onStrategyChange: (s: string) => void
  sizingMethod: 'fixed_notional' | 'volatility_scaled'
  onSizingChange: (s: 'fixed_notional' | 'volatility_scaled') => void
  initialCapital: number
  onCapitalChange: (n: number) => void
  strategies: string[]
}

export function PortfolioConfigPanel({
  strategy,
  onStrategyChange,
  sizingMethod,
  onSizingChange,
  initialCapital,
  onCapitalChange,
  strategies,
}: PortfolioConfigPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-xs uppercase text-text-secondary mb-1 font-mono">
          Strategy
        </p>
        <select
          className="w-full bg-bg-raised border border-border-default text-text-primary text-sm font-mono px-2 py-1 rounded"
          value={strategy}
          onChange={(e) => onStrategyChange(e.target.value)}
        >
          {strategies.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div>
        <p className="text-xs uppercase text-text-secondary mb-1 font-mono">
          Sizing Method
        </p>
        <div className="flex gap-1">
          {(['fixed_notional', 'volatility_scaled'] as const).map((m) => (
            <button
              key={m}
              onClick={() => onSizingChange(m)}
              className={`px-3 py-1 text-xs font-mono rounded border ${
                sizingMethod === m
                  ? 'bg-bg-accent border-border-strong text-text-primary'
                  : 'bg-bg-raised border-border-default text-text-secondary'
              }`}
            >
              {m === 'fixed_notional' ? 'Fixed Notional' : 'Vol Scaled'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs uppercase text-text-secondary mb-1 font-mono">
          Initial Capital (per asset)
        </p>
        <input
          type="number"
          className="w-full bg-bg-raised border border-border-default text-text-primary text-sm font-mono px-2 py-1 rounded"
          value={initialCapital}
          onChange={(e) => onCapitalChange(Number(e.target.value))}
          step={100000}
          min={100000}
        />
        <p className="text-xs text-text-secondary mt-1 font-mono">
          Running on all 6 commodity assets ·{' '}
          Total: {fmt.compactUsd(initialCapital * 6)}
        </p>
      </div>
    </div>
  )
}
