/**
 * ChartFrame — universal chart container.
 *
 * Provides: Panel chrome, four states (loading/error/empty/data), toolbar
 * (zoom-reset, PNG export, fullscreen), syncGroup ECharts connection,
 * and ChartFrameContext for child charts to register their ECharts instance.
 *
 * Fullscreen: re-renders children inside a new ChartFrameCtx.Provider inside
 * a Dialog at 90vw × 85vh. Creates a second independent ECharts instance.
 * When the Dialog closes, React unmounts the subtree and the child's cleanup
 * useEffect calls chart.dispose() automatically. Portal approach rejected —
 * it would couple chart components to ChartFrame resize signaling.
 *
 * Does NOT: fetch data, create ECharts instances, apply domain chart config.
 */
import { echarts, type ECharts } from '@/lib/echarts-setup'
import { createContext, useContext, useRef, useEffect, useState } from 'react'
import { Download, Maximize } from 'lucide-react'
import { Panel } from '@/ui/Panel'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import { ErrorState } from '@/components/layout/ErrorState'
import { EmptyState } from '@/components/layout/EmptyState'
import type { ApiClientError } from '@/api/client'
import { Dialog, DialogContent } from '@/ui/dialog'

// ---------------------------------------------------------------------------
// Context — child charts call onChartReady() to register their ECharts instance
// ---------------------------------------------------------------------------

interface ChartFrameContextValue {
  onChartReady: (instance: ECharts) => void
}

const ChartFrameCtx = createContext<ChartFrameContextValue | null>(null)

export function useChartFrame() {
  return useContext(ChartFrameCtx)
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChartFrameProps {
  title?: string
  titleExtra?: React.ReactNode
  height: number | string
  loading?: boolean
  error?: ApiClientError | Error | null
  empty?: { message: string; action?: { label: string; onClick: () => void } }
  toolbar?: boolean // default true
  actions?: React.ReactNode
  syncGroup?: string
  onRetry?: () => void
  className?: string
  children: React.ReactNode
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ChartFrame({
  title,
  titleExtra,
  height,
  loading,
  error,
  empty,
  toolbar = true,
  actions,
  syncGroup,
  onRetry,
  className,
  children,
}: ChartFrameProps) {
  const chartRef = useRef<ECharts | null>(null)
  const fullscreenChartRef = useRef<ECharts | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Called by child chart when its main ECharts instance is created
  function onChartReady(instance: ECharts) {
    chartRef.current = instance
    if (syncGroup) {
      instance.group = syncGroup
      echarts.connect(syncGroup)
    }
  }

  // Called by child chart when its fullscreen ECharts instance is created
  function onChartReadyFullscreen(instance: ECharts) {
    fullscreenChartRef.current = instance
  }

  // Disconnect syncGroup on unmount
  useEffect(() => {
    return () => {
      if (syncGroup) echarts.disconnect(syncGroup)
    }
  }, [syncGroup])

  function handleExport() {
    if (!chartRef.current) return
    const url = chartRef.current.getDataURL({ type: 'png', pixelRatio: 2 })
    const a = document.createElement('a')
    a.href = url
    a.download = `${title ?? 'chart'}-${Date.now()}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const toolbarEl = (toolbar || actions) ? (
    <div className="flex items-center gap-2">
      {actions}
      {toolbar && (
        <div className="flex items-center gap-1">
          <button
            onClick={handleExport}
            aria-label="Export chart as PNG"
            className="rounded-sm p-1 text-text-secondary transition-colors duration-fast hover:bg-bg-hover hover:text-text-primary"
          >
            <Download size={14} strokeWidth={1.75} />
          </button>
          <button
            onClick={() => setIsFullscreen(true)}
            aria-label="View fullscreen"
            className="rounded-sm p-1 text-text-secondary transition-colors duration-fast hover:bg-bg-hover hover:text-text-primary"
          >
            <Maximize size={14} strokeWidth={1.75} />
          </button>
        </div>
      )}
    </div>
  ) : undefined

  // Resolve which body to render based on state priority
  const body = (() => {
    if (loading) return <LoadingSkeleton variant="chart" />
    if (error) return <ErrorState error={error} onRetry={onRetry} />
    if (empty) return <EmptyState title={empty.message} body="" action={empty.action} />
    return children
  })()

  const heightStyle = typeof height === 'number' ? `${height}px` : height

  return (
    <ChartFrameCtx.Provider value={{ onChartReady }}>
      <Panel title={title} titleExtra={titleExtra} actions={toolbarEl} padding={false} className={className}>
        <div
          role="img"
          aria-label={title ? `${title} chart` : 'Chart'}
          style={{ height: heightStyle }}
          className="w-full overflow-hidden"
        >
          {body}
        </div>
      </Panel>

      {/* Fullscreen: re-render children in a new Provider + Dialog.
          Creates a second independent ECharts instance at fullscreen dimensions.
          Disposed automatically when Dialog unmounts via child cleanup useEffect. */}
      {isFullscreen && (
        <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
          <DialogContent
            style={{ width: '90vw', height: '85vh', maxWidth: 'none' }}
            className="bg-bg-panel p-0"
          >
            <ChartFrameCtx.Provider value={{ onChartReady: onChartReadyFullscreen }}>
              <div style={{ width: '100%', height: '100%' }}>{children}</div>
            </ChartFrameCtx.Provider>
          </DialogContent>
        </Dialog>
      )}
    </ChartFrameCtx.Provider>
  )
}
