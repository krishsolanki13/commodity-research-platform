import { render, screen } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { ICGateStrip } from '@/components/data/ICGateStrip'
import type { components } from '@/api/schema'

type SignalEvaluationData = components['schemas']['SignalEvaluationData']

const base = {
  turnover: 0.1,
  decay: [],
  evaluation_window: 100,
  computed_at: '2026-01-01T00:00:00Z',
}

const noiseEval: SignalEvaluationData = {
  ...base,
  ic: 0.0123,
  icir: 0.12,
  ic_band: 'noise',
}
const weakEval: SignalEvaluationData = {
  ...base,
  ic: 0.032,
  icir: 0.4,
  ic_band: 'weak_positive',
}
const strongEval: SignalEvaluationData = {
  ...base,
  ic: 0.061,
  icir: 0.72,
  ic_band: 'strong',
}

const onConfigure = vi.fn()
const onOverride = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ICGateStrip', () => {
  test('null evaluation renders locked state — button disabled', () => {
    render(
      <ICGateStrip evaluation={null} onConfigureBacktest={onConfigure} onOverride={onOverride} />
    )
    expect(screen.getByRole('button', { name: /configure backtest/i })).toBeDisabled()
    expect(screen.getByText(/evaluate this signal/i)).toBeInTheDocument()
  })

  test('noise evaluation renders disabled button', () => {
    render(
      <ICGateStrip
        evaluation={noiseEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByRole('button', { name: /configure backtest/i })).toBeDisabled()
    expect(screen.getByText(/signal likely noise/i)).toBeInTheDocument()
  })

  test('weak evaluation renders enabled button with caution note', () => {
    render(
      <ICGateStrip
        evaluation={weakEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByRole('button', { name: /configure backtest/i })).not.toBeDisabled()
    expect(screen.getByText(/WEAK SIGNAL — INVESTIGATE FURTHER/i)).toBeInTheDocument()
    expect(screen.getByText(/result may not be robust/i)).toBeInTheDocument()
  })

  test('strong evaluation renders enabled primary button', () => {
    render(
      <ICGateStrip
        evaluation={strongEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByRole('button', { name: /configure backtest/i })).not.toBeDisabled()
    expect(screen.getByText(/meaningful signal/i)).toBeInTheDocument()
  })

  test('override link is present in ALL four states', () => {
    const { rerender } = render(
      <ICGateStrip evaluation={null} onConfigureBacktest={onConfigure} onOverride={onOverride} />
    )
    expect(screen.getByText(/backtest without evaluation/i)).toBeInTheDocument()

    rerender(
      <ICGateStrip
        evaluation={noiseEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByText(/backtest without evaluation/i)).toBeInTheDocument()

    rerender(
      <ICGateStrip
        evaluation={weakEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByText(/backtest without evaluation/i)).toBeInTheDocument()

    rerender(
      <ICGateStrip
        evaluation={strongEval}
        onConfigureBacktest={onConfigure}
        onOverride={onOverride}
      />
    )
    expect(screen.getByText(/backtest without evaluation/i)).toBeInTheDocument()
  })
})
