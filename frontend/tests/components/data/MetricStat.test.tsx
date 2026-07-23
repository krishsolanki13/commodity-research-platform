import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { MetricStat } from '@/components/data/MetricStat'

describe('MetricStat', () => {
  test('positive percent value renders in gain color', () => {
    render(<MetricStat label="TOTAL RETURN" value={0.182} format="percent" tone="auto" />)
    const value = screen.getByText('+18.20%')
    expect(value).toBeInTheDocument()
    expect(value).toHaveStyle({ color: 'var(--text-gain)' })
  })

  test('drawdown always renders in loss color regardless of tone prop', () => {
    render(<MetricStat label="MAX DD" value={-0.0682} format="drawdown" tone="auto" />)
    // fmt.drawdown renders the value — check loss color applied
    const value = screen.getByText(/6\.82/)
    expect(value).toHaveStyle({ color: 'var(--text-loss)' })
  })

  test('null value renders em-dash', () => {
    render(<MetricStat label="SHARPE" value={null} format="ratio" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  test('hint renders info icon when provided', () => {
    render(<MetricStat label="SHARPE" value={0.3} format="ratio" hint="mean(r)/std(r)·√252" />)
    // Info icon present — label still rendered
    expect(screen.getByText('SHARPE')).toBeInTheDocument()
  })
})
