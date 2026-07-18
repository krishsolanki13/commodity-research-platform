import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { queryClient as qc } from '@/app/queryClient'
import { CurveComparison } from '@/screens/intelligence/CurveComparison'

beforeEach(() => qc.clear())

function Wrapper({ url = '/intelligence/compare' }: { url?: string }) {
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/intelligence/compare" element={<CurveComparison />} />
          <Route path="/intelligence" element={<div data-testid="intelligence" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('CurveComparison', () => {
  it('renders EmptyState when no ?assets= in URL', async () => {
    render(<Wrapper url="/intelligence/compare" />)
    await waitFor(() => screen.getByText(/select assets to compare/i))
  })

  it('renders CurveComparisonChart when 2 assets in URL', async () => {
    render(<Wrapper url="/intelligence/compare?assets=gold,silver&n_contracts=4" />)
    await waitFor(
      () => { expect(document.body).not.toBeEmptyDOMElement() },
      { timeout: 5000 }
    )
    const checkboxes = screen.getAllByRole('checkbox')
    const goldCheckbox = checkboxes.find(cb =>
      cb.getAttribute('aria-label')?.toLowerCase().includes('gold')
    )
    expect(goldCheckbox).toBeDefined()
  })

  it('max 4 assets: 5th checkbox disabled', async () => {
    render(
      <Wrapper url="/intelligence/compare?assets=gold,silver,copper,wti&n_contracts=4" />
    )
    await waitFor(
      () => screen.getAllByRole('checkbox').length >= 4,
      { timeout: 5000 }
    )
    const checkboxes = screen.getAllByRole('checkbox')
    const uncheckedDisabled = checkboxes.find(
      cb => !(cb as HTMLInputElement).checked && (cb as HTMLInputElement).disabled
    )
    expect(uncheckedDisabled).toBeDefined()
  })
})
