import { fmt } from '@/lib/fmt'
import { useStrategies } from '@/api/hooks/useStrategies'
import { Combobox } from '@/ui/Combobox'
import { validatePortfolioDateRange } from '@/features/portfolio/portfolioUrlState'

interface PortfolioConfigPanelProps {
  strategy: string
  onStrategyChange: (s: string) => void
  sizingMethod: 'fixed_notional' | 'volatility_scaled'
  onSizingChange: (s: 'fixed_notional' | 'volatility_scaled') => void
  initialCapital: number
  onCapitalChange: (n: number) => void
  fromDate: string
  onFromDateChange: (v: string) => void
  toDate: string
  onToDateChange: (v: string) => void
}

export function PortfolioConfigPanel({
  strategy,
  onStrategyChange,
  sizingMethod,
  onSizingChange,
  initialCapital,
  onCapitalChange,
  fromDate,
  onFromDateChange,
  toDate,
  onToDateChange,
}: PortfolioConfigPanelProps) {
  const { data: strategiesData } = useStrategies()
  const strategyOptions = (strategiesData?.strategies ?? []).map((s) => ({
    value: s.name,
    label: s.display_name,
  }))

  const dateErrors = validatePortfolioDateRange(fromDate, toDate)

  return (
    <div className="flex flex-col gap-4">
      <div className="gap-1.5 flex flex-col">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Strategy
        </span>
        <Combobox
          options={strategyOptions}
          value={strategy}
          onChange={onStrategyChange}
          placeholder="Select a strategy..."
          aria-label="Select portfolio strategy"
        />
      </div>

      <div>
        <p className="mb-1 font-mono text-xs uppercase text-text-secondary">Sizing Method</p>
        <div className="flex w-full gap-1">
          {(['fixed_notional', 'volatility_scaled'] as const).map((m) => (
            <button
              key={m}
              onClick={() => onSizingChange(m)}
              className={`flex-1 rounded border px-3 py-1 font-mono text-xs ${
                sizingMethod === m
                  ? 'bg-bg-accent border-border-strong text-text-primary'
                  : 'border-border-default bg-bg-raised text-text-secondary'
              }`}
            >
              {m === 'fixed_notional' ? 'Fixed Notional' : 'Vol Scaled'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label
          htmlFor="portfolio-initial-capital"
          className="mb-1 block font-mono text-xs uppercase text-text-secondary"
        >
          Initial Capital (per asset)
        </label>
        <input
          id="portfolio-initial-capital"
          type="number"
          className="w-full rounded border border-border-default bg-bg-raised px-2 py-1 font-mono text-sm text-text-primary"
          value={initialCapital}
          onChange={(e) => onCapitalChange(Number(e.target.value))}
          step={100000}
          min={100000}
        />
        <p className="mt-1 font-mono text-xs text-text-secondary">
          Running on all 6 commodity assets · Total: {fmt.compactUsd(initialCapital * 6)}
        </p>
      </div>

      <div className="gap-1.5 flex flex-col">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Date Range
        </span>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={fromDate}
            onChange={(e) => onFromDateChange(e.target.value)}
            placeholder="2020-01-01"
            className="py-1.5 rounded border border-border-strong bg-bg-raised px-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
            aria-label="From date"
          />
          <span className="text-xs text-text-secondary">→</span>
          <input
            type="date"
            value={toDate}
            onChange={(e) => onToDateChange(e.target.value)}
            placeholder="2022-12-31"
            className="py-1.5 rounded border border-border-strong bg-bg-raised px-2 font-mono text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-focus-ring"
            aria-label="To date"
          />
        </div>
        <p className="text-xs text-text-disabled">
          Leave blank to use full history (2010–2026)
        </p>
        {(dateErrors.fromDate || dateErrors.toDate) && (
          <p className="text-xs text-loss" role="alert">
            {dateErrors.fromDate ?? dateErrors.toDate}
          </p>
        )}
      </div>
    </div>
  )
}
