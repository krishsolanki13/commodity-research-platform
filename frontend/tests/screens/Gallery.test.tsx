import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import Gallery from '@/screens/dev/Gallery'

describe('Gallery', () => {
  test('renders all section headings without errors', () => {
    render(<Gallery />)
    expect(screen.getByRole('heading', { name: /Buttons/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /MetricGrid/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Panel/i })).toBeInTheDocument()
  })

  test('ICGateStrip null state renders in gallery', () => {
    render(<Gallery />)
    expect(
      screen.getByText(/EVALUATE THIS SIGNAL TO UNLOCK BACKTESTING/i)
    ).toBeInTheDocument()
  })
})
