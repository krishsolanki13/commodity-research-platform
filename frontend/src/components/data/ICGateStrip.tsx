import type { components } from '@/api/schema'
import { fmt } from '@/lib/fmt'
import { cn } from '@/lib/cn'
import { Button } from '@/ui/button'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'

type SignalEvaluationData = components['schemas']['SignalEvaluationData']
type ICBand = NonNullable<SignalEvaluationData['ic_band']>

interface ICGateStripProps {
  evaluation: SignalEvaluationData | null
  onConfigureBacktest: () => void
  onOverride: () => void
  loading?: boolean
}

function getBandColor(band: ICBand | null): string {
  if (band === 'strong' || band === 'inverse_meaningful') return 'var(--ic-strong)'
  if (band === 'weak_positive' || band === 'weak_inverse') return 'var(--ic-weak)'
  return 'var(--ic-noise)'
}

function getBgClass(band: ICBand | null): string {
  if (band === 'strong' || band === 'inverse_meaningful') return 'ic-gate-bg-strong'
  if (band === 'weak_positive' || band === 'weak_inverse') return 'ic-gate-bg-weak'
  return 'ic-gate-bg-noise'
}

function getVerdictText(band: ICBand | null): string {
  if (band === null) return 'EVALUATE THIS SIGNAL TO UNLOCK BACKTESTING'
  switch (band) {
    case 'noise':             return 'SIGNAL LIKELY NOISE'
    case 'weak_positive':
    case 'weak_inverse':      return 'WEAK SIGNAL — INVESTIGATE FURTHER'
    case 'strong':            return 'MEANINGFUL SIGNAL — BACKTEST WARRANTED'
    case 'inverse_meaningful':return 'INVERSE SIGNAL — BACKTEST WARRANTED (INVERT THRESHOLD)'
  }
}

function getThresholdText(band: ICBand | null): string {
  if (band === null) return 'Compute IC before launching a backtest'
  switch (band) {
    case 'noise':
      return '|IC| < 0.02 — signal is likely random. Investigate further or try different parameters.'
    case 'weak_positive':
    case 'weak_inverse':
      return '0.02 ≤ |IC| < 0.05 — some predictive content, but fragile.'
    case 'strong':
    case 'inverse_meaningful':
      return '|IC| ≥ 0.05 — meaningful predictive content.'
  }
}

export function ICGateStrip({
  evaluation,
  onConfigureBacktest,
  onOverride,
  loading = false,
}: ICGateStripProps) {
  if (loading) {
    return <LoadingSkeleton variant="form" className="min-h-20 px-6 py-4" />
  }

  const band = evaluation?.ic_band ?? null
  const bandColor = getBandColor(band)
  const bgClass = getBgClass(band)

  const isEnabled =
    evaluation !== null &&
    band !== 'noise' &&
    band !== null
  const isWeak = band === 'weak_positive' || band === 'weak_inverse'

  return (
    <div
      className={cn(
        'flex min-h-20 w-full items-center gap-8 border border-border-default px-6 py-4',
        bgClass
      )}
      style={{ borderLeft: `3px solid ${bandColor}` }}
    >
      {/* Left: verdict + threshold */}
      <div className="flex flex-1 flex-col gap-1">
        <span
          style={{ color: bandColor }}
          className="text-xs font-semibold uppercase tracking-widest"
        >
          {getVerdictText(band)}
        </span>
        <span className="text-xs text-text-secondary">
          {getThresholdText(band)}
        </span>
      </div>

      {/* Center: IC + ICIR hero metrics */}
      <div className="flex gap-8">
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-xs text-text-secondary">IC</span>
          <span
            style={{ color: bandColor }}
            className="font-mono text-metric-lg"
          >
            {evaluation?.ic != null ? fmt.ic(evaluation.ic) : '—'}
          </span>
        </div>
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-xs text-text-secondary">ICIR</span>
          <span
            style={{ color: bandColor }}
            className="font-mono text-metric"
          >
            {evaluation?.icir != null ? fmt.ic(evaluation.icir) : '—'}
          </span>
        </div>
      </div>

      {/* Right: actions */}
      <div className="flex flex-col items-end gap-1.5">
        <Button
          variant={isEnabled && !isWeak ? 'primary' : 'outline'}
          disabled={!isEnabled}
          aria-disabled={!isEnabled}
          onClick={isEnabled ? onConfigureBacktest : undefined}
        >
          Configure backtest →
        </Button>
        {isWeak && (
          <span className="text-xs text-warn">
            Weak signal — result may not be robust
          </span>
        )}
        {/* Override link — ALWAYS PRESENT in every state */}
        <button
          onClick={onOverride}
          className="text-xs text-text-secondary underline underline-offset-2 hover:text-text-primary"
        >
          Backtest without evaluation — will be recorded
        </button>
      </div>
    </div>
  )
}
