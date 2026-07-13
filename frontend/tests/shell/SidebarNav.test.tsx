import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, test, expect } from 'vitest'
import { SidebarNav } from '@/app/shell/SidebarNav'

function renderNav(initialPath = '/market') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <SidebarNav />
    </MemoryRouter>
  )
}

describe('SidebarNav', () => {
  test('renders all 7 nav items', () => {
    renderNav()
    expect(screen.getByRole('link', { name: /market/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /research/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /backtest/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /runs/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /system/i })).toBeInTheDocument()
    // Phase-gated items render as divs, not links
    expect(screen.getByText(/intelligence/i)).toBeInTheDocument()
    expect(screen.getByText(/portfolio/i)).toBeInTheDocument()
  })

  test('phase-gated items have aria-disabled="true"', () => {
    renderNav()
    const intel = screen.getByText(/intelligence/i).closest('[aria-disabled]')
    expect(intel).toHaveAttribute('aria-disabled', 'true')
    const portfolio = screen.getByText(/portfolio/i).closest('[aria-disabled]')
    expect(portfolio).toHaveAttribute('aria-disabled', 'true')
  })

  test('active route item has aria-current="page"', () => {
    renderNav('/market')
    expect(
      screen.getByRole('link', { name: /market/i })
    ).toHaveAttribute('aria-current', 'page')
  })

  test('collapse toggle button is present', () => {
    renderNav()
    expect(
      screen.getByRole('button', { name: /collapse|expand/i })
    ).toBeInTheDocument()
  })
})
