import { render } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { ScreePlot } from '@/components/charts/ScreePlot'
import { mockChartInstance } from '../../setup'

describe('ScreePlot', () => {
  beforeEach(() => {
    mockChartInstance.setOption.mockClear()
  })

  it('renders without crashing with mock EVR data', () => {
    expect(() =>
      render(
        <ScreePlot
          evr={[0.98, 0.015, 0.005]}
          cumEvr={[0.98, 0.995, 1.0]}
          pcLabels={['PC1', 'PC2', 'PC3']}
        />,
      ),
    ).not.toThrow()
    expect(mockChartInstance.setOption).toHaveBeenCalled()
  })
})
