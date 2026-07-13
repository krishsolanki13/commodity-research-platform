import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'

describe('RunStatusBadge', () => {
  test('complete status renders', () => {
    render(<RunStatusBadge status="complete" />)
    expect(screen.getByText('complete')).toBeInTheDocument()
  })

  test('failed status renders', () => {
    render(<RunStatusBadge status="failed" />)
    expect(screen.getByText('failed')).toBeInTheDocument()
  })

  test('running status renders', () => {
    render(<RunStatusBadge status="running" />)
    expect(screen.getByText('running')).toBeInTheDocument()
  })

  test('queued status renders', () => {
    render(<RunStatusBadge status="queued" />)
    expect(screen.getByText('queued')).toBeInTheDocument()
  })
})
