/**
 * Tree-shaken ECharts registration.
 *
 * IMPORT RULES (enforced by F3 acceptance criteria):
 * 1. This is the ONLY file that imports from 'echarts/charts', 'echarts/components',
 *    or 'echarts/renderers'. All other files import { echarts } from '@/lib/echarts-setup'.
 * 2. Imported once as a side-effect in AppShell.tsx before any ECharts instance is created.
 * 3. Never import * as echarts from 'echarts' anywhere — that loads the full 1MB+ bundle.
 *
 * Tree-shaking reduces the ECharts chunk from ~1MB to ~350KB.
 */
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart, BarChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  AxisPointerComponent,
  VisualMapComponent,
  TitleComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  CandlestickChart,
  LineChart,
  BarChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  AxisPointerComponent,
  VisualMapComponent,
  TitleComponent,
  CanvasRenderer,
])

export { echarts }
export type { EChartsType as ECharts } from 'echarts/core'
