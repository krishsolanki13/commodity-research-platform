import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import { FuturesCurve } from '@/screens/intelligence/FuturesCurve'

// MSW handlers (curveHandlers) are registered globally in tests/setup.ts
// via the handlers/index.ts update from Increment 1.
// goldCurveSnapshotFixture has regime: 'contango', 4 points.

function renderScreen(path = '/intelligence') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <FuturesCurve />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('FuturesCurve screen (S9)', () => {
  it('renders EmptyState with asset selection prompt when no ?asset= in URL', async () => {
    renderScreen('/intelligence')

    await waitFor(() => {
      expect(screen.getByText(/select an asset to view the futures curve/i)).toBeTruthy()
    })
  })

  it('renders content sections when ?asset=gold is in URL', async () => {
    renderScreen('/intelligence?asset=gold&n_contracts=6&lookback=3Y')

    // CurveKPIRow renders a Regime cell; check it eventually appears
    await waitFor(
      () => {
        expect(screen.getByText(/regime/i)).toBeTruthy()
      },
      { timeout: 5000 }
    )
  })

  it("shows 'CONTANGO' regime badge after snapshot loads for Gold", async () => {
    renderScreen('/intelligence?asset=gold&n_contracts=6&lookback=3Y')

    await waitFor(
      () => {
        expect(screen.getByText('CONTANGO')).toBeTruthy()
      },
      { timeout: 5000 }
    )
  })

  it('renders screen without crash when a different asset is in URL', () => {
    // silver fixture returns same goldCurveSnapshotFixture shape from MSW
    expect(() => renderScreen('/intelligence?asset=silver')).not.toThrow()
  })
})
