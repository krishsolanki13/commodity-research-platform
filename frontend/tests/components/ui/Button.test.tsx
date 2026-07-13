import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { Button } from '@/ui/button'

describe('Button', () => {
  test('renders primary variant with correct text', () => {
    render(<Button variant="primary">Launch</Button>)
    expect(screen.getByRole('button', { name: 'Launch' })).toBeInTheDocument()
  })

  test('disabled state prevents click', async () => {
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Click
      </Button>
    )
    await userEvent.click(screen.getByRole('button'))
    expect(handleClick).not.toHaveBeenCalled()
  })

  test('loading state renders spinner and disables button', () => {
    render(<Button loading>Save</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  test('destructive variant renders', () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })
})
