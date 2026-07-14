import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { EmptyState } from '@/components/layout/EmptyState'

describe('EmptyState', () => {
  test('renders title and body text', () => {
    render(<EmptyState title="No runs yet" body="Evaluate a signal first." />)
    expect(screen.getByText('No runs yet')).toBeInTheDocument()
    expect(screen.getByText('Evaluate a signal first.')).toBeInTheDocument()
  })

  test('renders action button when action prop provided', async () => {
    const handleClick = vi.fn()
    render(
      <EmptyState
        title="Empty"
        body="Body"
        action={{ label: 'Go to Workbench', onClick: handleClick }}
      />
    )
    await userEvent.click(screen.getByRole('button', { name: 'Go to Workbench' }))
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
