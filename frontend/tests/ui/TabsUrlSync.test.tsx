import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, test, expect } from 'vitest'
import { TabsUrlSync } from '@/ui/TabsUrlSync'

const DEFAULT_TABS = [
  { value: 'overview', label: 'Overview', content: <div>Overview</div> },
  { value: 'signal', label: 'Signal Quality', content: <div>Signal</div> },
  { value: 'trades', label: 'Trades', content: <div>Trades</div> },
]

function renderTabs(initialUrl = '/', extraProps = {}) {
  return render(
    <MemoryRouter initialEntries={[initialUrl]}>
      <TabsUrlSync tabs={DEFAULT_TABS} defaultTab="overview" {...extraProps} />
    </MemoryRouter>
  )
}

describe('TabsUrlSync', () => {
  test('renders the first tab as selected when no ?tab= param is present', () => {
    renderTabs('/')
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Signal Quality' })).not.toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  test('clicking a tab marks it as selected', async () => {
    renderTabs('/')
    await userEvent.click(screen.getByRole('tab', { name: 'Signal Quality' }))
    expect(screen.getByRole('tab', { name: 'Signal Quality' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
    expect(screen.getByRole('tab', { name: 'Overview' })).not.toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  test('an invalid ?tab= value falls back to the default tab', () => {
    renderTabs('/?tab=nonexistent')
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
  })
})
