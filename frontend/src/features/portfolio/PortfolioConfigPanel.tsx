import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'
import { rangeToDateParams } from '@/lib/date-range'
import { useStrategies } from '@/api/hooks/useStrategies'
import { Combobox } from '@/ui/Combobox'
import { validatePortfolioDateRange } from '@/features/portfolio/portfolioUrlState'

const PORTFOLIO_PRESETS = ['1Y', '3Y', '5Y', 'MAX'] as const
type PortfolioPreset = (typeof PORTFOLIO_PRESETS)[number]

function portfolioPresetToDates(preset: PortfolioPreset): { from: string; to: string } {
  if (preset === 'MAX') return { from: '', to: '' }
  const { from_date, to_date } = rangeToDateParams(preset)
  return { from: from_date, to: to_date }
}

function detectActivePreset(from: string, to: string): PortfolioPreset | null {
  if (!from && !to) return 'MAX'
  for (const preset of ['1Y', '3Y', '5Y'] as const) {
    const expected = portfolioPresetToDates(preset)
    if (from === expected.from && to === expected.to) return preset
  }
  return null
}

interface PortfolioConfigPanelProps {
  strategy: string
  onStrategyChange: (s: string) => void
  sizingMethod: 'fixed_notional' | 'volatility_scaled'
  onSizingChange: (s: 'fixed_notional' | 'volatility_scaled') => void
  initialCapital: number
  onCapitalChange: (n: number) => void
  fromDate: string
  toDate: string
  onDateRangeChange: (range: { from: string; to: string }) => void
}

export function PortfolioConfigPanel({
  strategy,
  onStrategyChange,
  sizingMethod,
  onSizingChange,
  initialCapital,
  onCapitalChange,
  fromDate,
  toDate,
  onDateRangeChange,
}: PortfolioConfigPanelProps) {
  const { data: strategiesData } = useStrategies()
  const strategyOptions = (strategiesData?.strategies ?? []).map((s) => ({
    value: s.name,
    label: s.display_name,
  }))

  const dateErrors = validatePortfolioDateRange(fromDate, toDate)
  const activePreset = detectActivePreset(fromDate, toDate)

  function handleDateChange({ from, to }: { from: string; to: string }) {
    onDateRangeChange({ from, to })
  }

  function handleFromBlur(from: string) {
    let nextTo = toDate
    if (from && nextTo && from > nextTo) nextTo = from
    handleDateChange({ from, to: nextTo })
  }

  function handleToBlur(to: string) {
    let nextFrom = fromDate
    if (to && nextFrom && to < nextFrom) nextFrom = to
    handleDateChange({ from: nextFrom, to })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        <p className="text-sm text-text-secondary">
          {fromDate || '—'} → {toDate || '—'}
        </p>

        <div className="flex flex-wrap gap-1">
          {PORTFOLIO_PRESETS.map((preset) => {
            const isActive = activePreset === preset
            return (
              <button
                key={preset}
                type="button"
                onClick={() => handleDateChange(portfolioPresetToDates(preset))}
                className={cn(
                  'rounded-sm border border-border-strong px-2 py-1',
                  'font-mono text-xs',
                  'hover:bg-bg-hover hover:text-text-primary',
                  isActive
                    ? 'bg-bg-hover text-text-primary'
                    : 'text-text-secondary'
                )}
              >
                {preset}
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            aria-label="From date"
            value={fromDate}
            onChange={(e) => handleDateChange({ from: e.target.value, to: toDate })}
            onBlur={(e) => handleFromBlur(e.target.value)}
            className={cn(
              'h-[var(--input-height)] flex-1 rounded-sm border border-border-strong bg-bg-app',
              'px-3 font-mono text-sm text-text-primary',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          />
          <span className="text-xs text-text-secondary">→</span>
          <input
            type="text"
            aria-label="To date"
            value={toDate}
            onChange={(e) => handleDateChange({ from: fromDate, to: e.target.value })}
            onBlur={(e) => handleToBlur(e.target.value)}
            className={cn(
              'h-[var(--input-height)] flex-1 rounded-sm border border-border-strong bg-bg-app',
              'px-3 font-mono text-sm text-text-primary',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
            )}
          />
        </div>

        {(dateErrors.fromDate || dateErrors.toDate) && (
          <p className="text-xs text-loss" role="alert">
            {dateErrors.fromDate ?? dateErrors.toDate}
          </p>
        )}
      </div>

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
    </div>
  )
}
