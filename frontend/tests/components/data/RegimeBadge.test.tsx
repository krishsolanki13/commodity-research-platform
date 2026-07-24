import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { RegimeBadge } from '@/components/data/RegimeBadge'

describe('RegimeBadge', () => {
  it("renders 'CONTANGO' label with warn-500 styling for contango regime", () => {
    const { container } = render(<RegimeBadge regime="contango" />)
    const badge = container.firstChild as HTMLElement

    expect(badge).toBeTruthy()
    expect(badge.textContent).toBe('CONTANGO')
    expect(badge.getAttribute('role')).toBe('status')
    expect(badge.getAttribute('aria-label')).toBe('contango regime')
    // Verify warn color class is applied (token name per transfer package)
    expect(badge.className).toContain('text-warn')
  })

  it("renders 'BACKWARDATION' label with gain-500 styling for backwardation regime", () => {
    const { container } = render(<RegimeBadge regime="backwardation" />)
    const badge = container.firstChild as HTMLElement

    expect(badge.textContent).toBe('BACKWARDATION')
    expect(badge.className).toContain('text-gain')
  })

  it('renders em dash for null regime', () => {
    const { container } = render(<RegimeBadge regime={null} />)
    const badge = container.firstChild as HTMLElement

    expect(badge.textContent).toBe('—')
    expect(badge.getAttribute('aria-label')).toBe('regime unknown')
  })

  it('renders with horizontal padding', () => {
    const { container } = render(<RegimeBadge regime="contango" />)
    expect(container.firstChild).toHaveClass('px-3')
  })
})
