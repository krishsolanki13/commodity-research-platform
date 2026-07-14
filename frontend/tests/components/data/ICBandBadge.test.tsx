import { render, screen } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import { ICBandBadge } from '@/components/data/ICBandBadge'

describe('ICBandBadge', () => {
  test('ic=0.061 renders strong band label', () => {
    render(<ICBandBadge ic={0.061} />)
    expect(screen.getByText(/strong/)).toBeInTheDocument()
  })

  test('ic=0.0123 renders noise band — Gold EMA 50/200 real value', () => {
    render(<ICBandBadge ic={0.0123} />)
    expect(screen.getByText(/noise/)).toBeInTheDocument()
  })

  test('ic=null renders em-dash in noise band', () => {
    render(<ICBandBadge ic={null} />)
    expect(screen.getByText(/—/)).toBeInTheDocument()
  })
})
