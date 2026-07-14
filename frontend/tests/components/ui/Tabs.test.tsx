import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, test, expect } from 'vitest'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/tabs'

const TabsFixture = ({ defaultValue = 'overview' }: { defaultValue?: string }) => (
  <Tabs defaultValue={defaultValue}>
    <TabsList>
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="trades">Trades</TabsTrigger>
    </TabsList>
    <TabsContent value="overview">
      <p>Overview content</p>
    </TabsContent>
    <TabsContent value="trades">
      <p>Trades content</p>
    </TabsContent>
  </Tabs>
)

describe('Tabs', () => {
  test('default tab renders first panel', () => {
    render(<TabsFixture />)
    expect(screen.getByText('Overview content')).toBeInTheDocument()
  })

  test('clicking tab switches content', async () => {
    render(<TabsFixture />)
    await userEvent.click(screen.getByRole('tab', { name: 'Trades' }))
    expect(screen.getByText('Trades content')).toBeVisible()
  })

  test('clicking tab updates aria-selected', async () => {
    render(
      <MemoryRouter>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trades">Trades</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <p>Overview</p>
          </TabsContent>
          <TabsContent value="trades">
            <p>Trades</p>
          </TabsContent>
        </Tabs>
      </MemoryRouter>
    )
    const tradesTab = screen.getByRole('tab', { name: 'Trades' })
    await userEvent.click(tradesTab)
    expect(tradesTab).toHaveAttribute('aria-selected', 'true')
  })
})
