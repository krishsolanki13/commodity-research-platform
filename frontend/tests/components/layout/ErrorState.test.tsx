import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { ErrorState } from '@/components/layout/ErrorState'

describe('ErrorState', () => {
  test('renders error message', () => {
    render(<ErrorState error={{ message: 'Asset not found.' }} />)
    expect(screen.getByText('Asset not found.')).toBeInTheDocument()
  })

  test('renders retry button and fires onRetry', async () => {
    const handleRetry = vi.fn()
    render(<ErrorState error={{ message: 'Error' }} onRetry={handleRetry} />)
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(handleRetry).toHaveBeenCalledOnce()
  })
})
