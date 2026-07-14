import { useState } from 'react'
import type { components } from '@/api/schema'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import { Input } from '@/ui/input'
import { NumberInput } from '@/ui/NumberInput'
import { Badge } from '@/ui/badge'
import { Separator } from '@/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/ui/dialog'
import { RunStatusBadge } from '@/components/data/RunStatusBadge'
import { ICBandBadge } from '@/components/data/ICBandBadge'
import { MetricStat } from '@/components/data/MetricStat'
import { MetricGrid } from '@/components/data/MetricGrid'
import { ICGateStrip } from '@/components/data/ICGateStrip'
import { EmptyState } from '@/components/layout/EmptyState'
import { ErrorState } from '@/components/layout/ErrorState'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { Combobox } from '@/ui/Combobox'
import { ChartFrame } from '@/components/charts/ChartFrame'
import { PriceChart } from '@/components/charts/PriceChart'
import { EquityCurveChart } from '@/components/charts/EquityCurveChart'
import { Sparkline } from '@/components/charts/Sparkline'
import { DataGrid } from '@/components/data/DataGrid'
import { createColumnHelper } from '@tanstack/react-table'

type SignalEvaluationData = components['schemas']['SignalEvaluationData']
type ColumnarSeries = components['schemas']['ColumnarSeries']

// Gold OHLCV fixture — 5 bars (2021-01-01 through 2021-01-05)
const GOLD_OHLCV: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000, 1609804800000],
  columns: {
    open: [1898.0, 1902.5, 1910.0, 1905.0, 1915.0],
    high: [1908.0, 1915.0, 1918.0, 1912.0, 1925.0],
    low: [1892.0, 1898.0, 1903.0, 1900.0, 1908.0],
    close: [1902.5, 1910.0, 1905.0, 1910.0, 1920.0],
    volume: [12000, 14500, 11000, 13200, 15800],
  },
}

const EQUITY_FIXTURE: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000],
  columns: { value: [1000000, 1005000, 1003000, 1010000] },
}

const DRAWDOWN_FIXTURE: ColumnarSeries = {
  index: [1609459200000, 1609545600000, 1609632000000, 1609718400000],
  columns: { value: [0, -0.002, -0.003, 0] },
}

// ── ICGateStrip mock data ────────────────────────────────────────────
const evalBase = {
  turnover: 0.12,
  decay: [],
  evaluation_window: 252,
  computed_at: '2026-07-14T00:00:00Z',
}

const noiseEval: SignalEvaluationData = {
  ...evalBase,
  ic: 0.0123,
  icir: 0.12,
  ic_band: 'noise',
}
const weakEval: SignalEvaluationData = {
  ...evalBase,
  ic: 0.032,
  icir: 0.4,
  ic_band: 'weak_positive',
}
const strongEval: SignalEvaluationData = {
  ...evalBase,
  ic: 0.061,
  icir: 0.72,
  ic_band: 'strong',
}

// ── MetricGrid demo data ─────────────────────────────────────────────
const DEMO_METRICS = [
  { label: 'SHARPE', value: 0.3, format: 'ratio' as const },
  { label: 'MAX DD', value: -0.0682, format: 'drawdown' as const },
  { label: 'TOTAL RETURN', value: 0.182, format: 'percent' as const },
  { label: 'CAGR', value: 0.0092, format: 'percent' as const },
  {
    label: 'WIN RATE',
    value: 0.211,
    format: 'percent' as const,
    tone: 'neutral' as const,
  },
  {
    label: 'TRADES',
    value: 19,
    format: 'integer' as const,
    tone: 'neutral' as const,
  },
]

// ── Combobox demo options ────────────────────────────────────────────
const ASSET_OPTIONS = [
  { value: 'gold', label: 'Gold', meta: 'GC=F' },
  { value: 'wti', label: 'WTI Crude', meta: 'CL=F' },
  { value: 'natural_gas', label: 'Natural Gas', meta: 'NG=F' },
  { value: 'silver', label: 'Silver', meta: 'SI=F' },
]

// ── Section wrapper ──────────────────────────────────────────────────
function GallerySection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 font-mono text-lg text-text-secondary">{title}</h2>
      {children}
      <Separator className="mt-8" />
    </section>
  )
}

// ── Gallery screen ───────────────────────────────────────────────────
export default function Gallery() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [comboValue, setComboValue] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-bg-app p-8">
      <h1 className="text-2xl mb-2 font-mono text-text-emphasis">F2 Primitives Gallery</h1>
      <p className="mb-10 text-sm text-text-secondary">
        Dev-only route — every primitive in every state. Not linked from SidebarNav.
      </p>

      {/* ── 1. Buttons ───────────────────────────────────────────── */}
      <GallerySection title="1 · Buttons">
        <div className="flex flex-wrap gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="default">Default</Button>
          <Button variant="outline">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Danger</Button>
          <Button variant="primary" size="sm">
            Small Primary
          </Button>
          <Button variant="outline" size="sm">
            Small Secondary
          </Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
          <Button variant="primary" loading>
            Loading
          </Button>
        </div>
      </GallerySection>

      {/* ── 2. Inputs ────────────────────────────────────────────── */}
      <GallerySection title="2 · Inputs">
        <div className="flex max-w-sm flex-col gap-3">
          <Input placeholder="Text input" />
          <NumberInput value={50} onChange={() => undefined} unit="bars" placeholder="50" />
          <Combobox
            options={ASSET_OPTIONS}
            value={comboValue}
            onChange={setComboValue}
            placeholder="Select asset..."
            searchPlaceholder="Search assets..."
          />
        </div>
      </GallerySection>

      {/* ── 3. Tabs ──────────────────────────────────────────────── */}
      <GallerySection title="3 · Tabs">
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="trades">Trades</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <p className="p-4 text-sm text-text-secondary">Overview content</p>
          </TabsContent>
          <TabsContent value="trades">
            <p className="p-4 text-sm text-text-secondary">Trades content</p>
          </TabsContent>
          <TabsContent value="performance">
            <p className="p-4 text-sm text-text-secondary">Performance content</p>
          </TabsContent>
        </Tabs>
      </GallerySection>

      {/* ── 4. Dialog ────────────────────────────────────────────── */}
      <GallerySection title="4 · Dialog">
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline">Open Dialog</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Example Dialog</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-text-secondary">
              Focus is trapped inside this dialog. Esc closes it.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setDialogOpen(false)}>
                Confirm
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </GallerySection>

      {/* ── 5. Status Badges ─────────────────────────────────────── */}
      <GallerySection title="5 · Status Badges">
        <div className="flex flex-wrap gap-3">
          <RunStatusBadge status="queued" />
          <RunStatusBadge status="running" />
          <RunStatusBadge status="complete" />
          <RunStatusBadge status="failed" />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Badge>Default Badge</Badge>
          <ICBandBadge ic={0.061} />
          <ICBandBadge ic={0.032} />
          <ICBandBadge ic={0.0123} />
          <ICBandBadge ic={null} />
        </div>
      </GallerySection>

      {/* ── 6. MetricStat ────────────────────────────────────────── */}
      <GallerySection title="6 · MetricStat">
        <div className="flex flex-wrap gap-8">
          <MetricStat label="TOTAL RETURN" value={0.182} format="percent" tone="auto" />
          <MetricStat label="MAX DRAWDOWN" value={-0.0682} format="drawdown" />
          <MetricStat label="IC" value={0.0123} format="ic" tone="auto" />
          <MetricStat label="SHARPE (null)" value={null} format="ratio" />
          <MetricStat
            label="SHARPE"
            value={0.3}
            format="ratio"
            size="lg"
            hint="mean(daily_return) / std(daily_return) · √252"
          />
          <MetricStat label="CAGR" value={0.0092} format="percent" tone="auto" delta={0.0031} />
        </div>
      </GallerySection>

      {/* ── 7. MetricGrid ────────────────────────────────────────── */}
      <GallerySection title="7 · MetricGrid">
        <MetricGrid metrics={DEMO_METRICS} columns={6} />
        <div className="mt-4">
          <p className="mb-2 text-xs text-text-secondary">loading state</p>
          <MetricGrid metrics={[]} columns={4} loading={true} />
        </div>
      </GallerySection>

      {/* ── 8. ICGateStrip — all 4 states ────────────────────────── */}
      <GallerySection title="8 · ICGateStrip (all 4 states)">
        <div className="flex flex-col gap-4">
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">null — no evaluation yet</p>
            <ICGateStrip
              evaluation={null}
              onConfigureBacktest={() => undefined}
              onOverride={() => undefined}
            />
          </div>
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">
              noise — IC 0.0123 (Gold EMA 50/200 real value)
            </p>
            <ICGateStrip
              evaluation={noiseEval}
              onConfigureBacktest={() => undefined}
              onOverride={() => undefined}
            />
          </div>
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">weak — IC 0.032</p>
            <ICGateStrip
              evaluation={weakEval}
              onConfigureBacktest={() => undefined}
              onOverride={() => undefined}
            />
          </div>
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">strong — IC 0.061</p>
            <ICGateStrip
              evaluation={strongEval}
              onConfigureBacktest={() => undefined}
              onOverride={() => undefined}
            />
          </div>
        </div>
      </GallerySection>

      {/* ── 9. EmptyState + ErrorState ───────────────────────────── */}
      <GallerySection title="9 · EmptyState + ErrorState">
        <div className="grid grid-cols-2 gap-6">
          <Panel title="EmptyState">
            <EmptyState
              title="No runs yet"
              body="Evaluate a signal in the Workbench, then launch your first backtest."
              action={{ label: 'Open Workbench', onClick: () => undefined }}
            />
          </Panel>
          <Panel title="ErrorState">
            <ErrorState
              error={{ code: 'NOT_FOUND', message: 'Run not found.' }}
              onRetry={() => undefined}
            />
          </Panel>
        </div>
        <div className="mt-4">
          <p className="mb-2 text-xs text-text-secondary">compact variant</p>
          <Panel>
            <ErrorState
              error={{ message: 'Failed to load asset data.' }}
              onRetry={() => undefined}
              compact={true}
            />
          </Panel>
        </div>
      </GallerySection>

      {/* ── 10. LoadingSkeleton ──────────────────────────────────── */}
      <GallerySection title="10 · LoadingSkeleton">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="mb-2 text-xs text-text-secondary">metric-grid</p>
            <LoadingSkeleton variant="metric-grid" columns={4} />
          </div>
          <div>
            <p className="mb-2 text-xs text-text-secondary">chart</p>
            <LoadingSkeleton variant="chart" />
          </div>
          <div>
            <p className="mb-2 text-xs text-text-secondary">table (5 rows)</p>
            <LoadingSkeleton variant="table" rows={5} />
          </div>
          <div>
            <p className="mb-2 text-xs text-text-secondary">form</p>
            <LoadingSkeleton variant="form" />
          </div>
        </div>
      </GallerySection>

      {/* ── 11. Panel variants ───────────────────────────────────── */}
      <GallerySection title="11 · Panel">
        <div className="grid grid-cols-2 gap-6">
          <Panel
            title="With title and actions"
            actions={
              <Button size="sm" variant="ghost">
                Action
              </Button>
            }
          >
            <p className="text-sm text-text-secondary">Panel content here.</p>
          </Panel>
          <Panel>
            <p className="text-sm text-text-secondary">
              Panel without title — no header row rendered.
            </p>
          </Panel>
          <Panel title="No padding" padding={false}>
            <div className="bg-bg-raised p-4 text-sm text-text-secondary">
              padding=false — content flush to border.
            </div>
          </Panel>
        </div>
      </GallerySection>

      {/* ── 12. Charts ──────────────────────────────────────────────────────── */}
      <GallerySection title="Charts">
        <div className="flex flex-col gap-6">
          {/* ChartFrame states */}
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">ChartFrame — loading state</p>
            <ChartFrame height={160} loading={true} title="Loading">
              {null}
            </ChartFrame>
          </div>
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">ChartFrame — empty state</p>
            <ChartFrame height={160} empty={{ message: 'No data in this range.' }} title="Empty">
              {null}
            </ChartFrame>
          </div>

          {/* PriceChart */}
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">
              PriceChart — Gold fixture (5 bars, candlestick + volume)
            </p>
            <PriceChart ohlcv={GOLD_OHLCV} height={280} title="Gold · GC=F" />
          </div>

          {/* EquityCurveChart */}
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">
              EquityCurveChart — with drawdown pane + baseline
            </p>
            <EquityCurveChart
              equity={EQUITY_FIXTURE}
              drawdown={DRAWDOWN_FIXTURE}
              baseline={1000000}
              height={300}
              title="Equity Curve"
            />
          </div>

          {/* Sparklines */}
          <div>
            <p className="mb-1 font-mono text-xs text-text-secondary">Sparkline — tone variants</p>
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-text-secondary">Rising (auto):</span>
                <Sparkline values={[100, 105, 110, 108, 115]} tone="auto" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-text-secondary">Falling (auto):</span>
                <Sparkline values={[115, 110, 108, 105, 100]} tone="auto" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-text-secondary">Null gap:</span>
                <Sparkline values={[100, 105, null, 108, 115]} tone="auto" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-text-secondary">Explicit loss:</span>
                <Sparkline values={[100, 95, 90, 88, 85]} tone="loss" />
              </div>
            </div>
          </div>
        </div>
      </GallerySection>

      {/* ── 13. DataGrid ─────────────────────────────────────────────────────── */}
      <GallerySection title="DataGrid">
        {(() => {
          interface DemoRow {
            id: string
            asset: string
            value: number
            status: string
          }

          const colHelper = createColumnHelper<DemoRow>()
          const demoColumns = [
            colHelper.accessor('asset', {
              header: 'ASSET',
              cell: (i) => i.getValue(),
            }),
            colHelper.accessor('value', {
              header: 'VALUE',
              cell: (i) => <span className="font-mono">{i.getValue().toFixed(2)}</span>,
            }),
            colHelper.accessor('status', {
              header: 'STATUS',
              cell: (i) => i.getValue(),
            }),
          ]

          const smallData: DemoRow[] = [
            { id: '1', asset: 'gold', value: 1920.5, status: 'active' },
            { id: '2', asset: 'silver', value: 23.45, status: 'active' },
            { id: '3', asset: 'copper', value: 4.12, status: 'active' },
            { id: '4', asset: 'wti', value: 78.2, status: 'active' },
            { id: '5', asset: 'natural_gas', value: 2.85, status: 'active' },
          ]

          const largeData: DemoRow[] = Array.from({ length: 300 }, (_, i) => ({
            id: String(i),
            asset: ['gold', 'silver', 'copper'][i % 3],
            value: i * 10.5,
            status: 'active',
          }))

          return (
            <div className="flex flex-col gap-6">
              <div>
                <p className="mb-1 font-mono text-xs text-text-secondary">
                  DataGrid — 5 rows, search + CSV export toolbar
                </p>
                <div
                  className="overflow-hidden rounded-md border border-border-default"
                  style={{ height: 220 }}
                >
                  <DataGrid
                    columns={demoColumns}
                    data={smallData}
                    getRowId={(r) => r.id}
                    toolbar={{ search: true, export: true }}
                  />
                </div>
              </div>

              <div>
                <p className="mb-1 font-mono text-xs text-text-secondary">
                  DataGrid — 300 rows, virtualized
                </p>
                <div
                  className="overflow-hidden rounded-md border border-border-default"
                  style={{ height: 220 }}
                >
                  <DataGrid
                    columns={demoColumns}
                    data={largeData}
                    getRowId={(r) => r.id}
                    virtualized={true}
                  />
                </div>
              </div>
            </div>
          )
        })()}
      </GallerySection>
    </div>
  )
}
