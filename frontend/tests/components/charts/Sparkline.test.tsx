import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Sparkline } from '@/components/charts/Sparkline'

describe('Sparkline', () => {
  it('renders an SVG element', () => {
    const { container } = render(<Sparkline values={[1, 2, 3, 4, 5]} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('null values produce multiple polyline segments — gap policy', () => {
    const { container } = render(
      <Sparkline values={[1, 2, null, 4, 5]} />
    )
    // [1,2] → segment 1, [4,5] → segment 2 — two polylines, not one connected line
    const polylines = container.querySelectorAll('polyline')
    expect(polylines.length).toBeGreaterThanOrEqual(2)
  })

  it('rising series uses gain color with auto tone', () => {
    const { container } = render(
      <Sparkline values={[100, 110, 120, 130]} tone="auto" />
    )
    const svg = container.querySelector('svg')
    expect(svg).toBeTruthy()
    // Color is applied via style={{ color: 'var(--gain-500)' }} on the SVG element
    expect(container.innerHTML).toContain('gain')
  })
})
