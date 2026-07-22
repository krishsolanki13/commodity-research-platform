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
    expect(screen.getByRole('link', { name: /intelligence/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /portfolio/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /system/i })).toBeInTheDocument()
  })

  test('portfolio item links to the portfolio analytics screen', () => {
    renderNav('/portfolio')
    expect(screen.getByRole('link', { name: /portfolio/i })).toHaveAttribute('aria-current', 'page')
  })

  test('active route item has aria-current="page"', () => {
    renderNav('/market')
    expect(screen.getByRole('link', { name: /market/i })).toHaveAttribute('aria-current', 'page')
  })

  test('collapse toggle button is present', () => {
    renderNav()
    expect(screen.getByRole('button', { name: /collapse|expand/i })).toBeInTheDocument()
  })
})
