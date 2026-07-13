import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import { Dialog, DialogContent } from '@/ui/dialog'

describe('Dialog', () => {
  test('renders dialog content when open', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <p>Dialog body</p>
        </DialogContent>
      </Dialog>
    )
    expect(screen.getByText('Dialog body')).toBeInTheDocument()
  })

  test('calls onOpenChange(false) when Esc is pressed', async () => {
    const handleChange = vi.fn()
    render(
      <Dialog open={true} onOpenChange={handleChange}>
        <DialogContent>
          <p>Content</p>
        </DialogContent>
      </Dialog>
    )
    await userEvent.keyboard('{Escape}')
    expect(handleChange).toHaveBeenCalledWith(false)
  })

  test('does not render content when closed', () => {
    render(
      <Dialog open={false}>
        <DialogContent>
          <p>Hidden content</p>
        </DialogContent>
      </Dialog>
    )
    expect(screen.queryByText('Hidden content')).not.toBeInTheDocument()
  })
})
