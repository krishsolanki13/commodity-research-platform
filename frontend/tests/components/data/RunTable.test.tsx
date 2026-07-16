import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RunTable } from '@/components/data/RunTable'
import { runListFixture } from '../../mocks/fixtures/run-list'

const noop = vi.fn()
const noopSet = vi.fn<(ids: Set<string>) => void>()

describe('RunTable', () => {
  it('renders correct number of rows from runListFixture', () => {
    render(
      <RunTable
        rows={runListFixture.runs}
        onRowClick={noop}
        selection={{ ids: new Set(), onChange: noopSet }}
      />
    )
    const bodyRows = screen
      .getAllByRole('row')
      .filter((r) => r.closest('tbody') !== null)
    expect(bodyRows).toHaveLength(runListFixture.runs.length)
  })

  it('RunStatusBadge present in status cells', () => {
    render(
      <RunTable
        rows={runListFixture.runs}
        onRowClick={noop}
        selection={{ ids: new Set(), onChange: noopSet }}
      />
    )
    const badges = screen.getAllByText(/complete/i)
    expect(badges.length).toBeGreaterThanOrEqual(runListFixture.runs.length)
  })

  it('clicking a sortable column header calls onSort', async () => {
    const onSort = vi.fn()
    render(
      <RunTable
        rows={runListFixture.runs}
        onRowClick={noop}
        selection={{ ids: new Set(), onChange: noopSet }}
        onSort={onSort}
      />
    )
    const sharpeHeader = screen.getByRole('columnheader', { name: /sharpe/i })
    await userEvent.click(sharpeHeader)
    expect(onSort).toHaveBeenCalled()
  })

  it('loading=true renders LoadingSkeleton', () => {
    const { container } = render(
      <RunTable
        rows={[]}
        onRowClick={noop}
        selection={{ ids: new Set(), onChange: noopSet }}
        loading
      />
    )
    const skeleton = container.querySelector(
      '[data-testid="loading-skeleton"], .animate-pulse, [aria-busy="true"]'
    )
    expect(skeleton).not.toBeNull()
  })
})
