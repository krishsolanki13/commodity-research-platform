import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ComparisonTray } from '@/app/shell/ComparisonTray'
import { useComparisonBasket } from '@/stores/comparisonBasket'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderTray() {
  return render(
    <MemoryRouter>
      <ComparisonTray />
    </MemoryRouter>
  )
}

describe('ComparisonTray', () => {
  beforeEach(() => {
    useComparisonBasket.setState({ ids: [] })
    mockNavigate.mockReset()
  })

  it('renders null when basket is empty', () => {
    const { container } = renderTray()
    expect(container.firstChild).toBeNull()
  })

  it('renders pill with correct count when basket has 1 run', () => {
    useComparisonBasket.setState({ ids: ['run-1'] })
    renderTray()
    expect(screen.getByText('1 run selected')).toBeInTheDocument()
    expect(
      screen.getByText('Select 1 more run to compare')
    ).toBeInTheDocument()
  })

  it('Compare button is disabled with 1 run; navigates with correct URL with 2 runs', async () => {
    // 1-run state: button disabled
    useComparisonBasket.setState({ ids: ['run-1'] })
    const { unmount } = renderTray()
    const disabledBtn = screen.getByRole('button', { name: /compare/i })
    expect(disabledBtn).toBeDisabled()
    unmount()

    // 2-run state: button enabled, navigate fires correctly
    useComparisonBasket.setState({ ids: ['run-1', 'run-2'] })
    renderTray()
    const enabledBtn = screen.getByRole('button', { name: /compare/i })
    expect(enabledBtn).not.toBeDisabled()
    await userEvent.click(enabledBtn)
    expect(mockNavigate).toHaveBeenCalledWith(
      '/runs/compare?ids=run-1,run-2'
    )
  })
})
