import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, test, expect, vi } from 'vitest'
import { CommandPalette } from '@/app/shell/CommandPalette'

function renderPalette(open: boolean) {
  return render(
    <MemoryRouter>
      <CommandPalette open={open} onOpenChange={vi.fn()} />
    </MemoryRouter>
  )
}

describe('CommandPalette', () => {
  test('renders dialog when open=true', () => {
    renderPalette(true)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  test('does not render dialog when open=false', () => {
    renderPalette(false)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
