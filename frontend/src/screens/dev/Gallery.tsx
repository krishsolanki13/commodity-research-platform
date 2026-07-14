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

type SignalEvaluationData = components['schemas']['SignalEvaluationData']

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
    </div>
  )
}
