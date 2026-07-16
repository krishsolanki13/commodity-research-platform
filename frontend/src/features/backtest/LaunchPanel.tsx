/**
 * LaunchPanel — triggers backtest launch, polls for completion, calls onLaunched when done.
 * Does not navigate; parent owns navigation via onLaunched.
 */
import { useEffect, useState } from 'react'
import { useBacktestLaunch, useBacktestStatus } from '@/api/hooks'
import { ErrorState } from '@/components/layout/ErrorState'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import type { BacktestConfig } from './BacktestConfigPanel'
import type { components } from '@/api/schema'

type BacktestLaunchRequest = components['schemas']['BacktestLaunchRequest']
type SignalEvaluationData = components['schemas']['SignalEvaluationData']

interface LaunchPanelProps {
  config: BacktestConfig
  evalSummary: SignalEvaluationData | null
  evalOverride: boolean
  launchRequest: BacktestLaunchRequest
  onLaunched: (runId: string) => void
}

export function LaunchPanel({
  config: _config,
  evalSummary: _evalSummary,
  evalOverride: _evalOverride,
  launchRequest,
  onLaunched,
}: LaunchPanelProps) {
  const [pollingRunId, setPollingRunId] = useState<string | null>(null)
  const [launchTime, setLaunchTime] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState(0)

  const launch = useBacktestLaunch()
  const status = useBacktestStatus(pollingRunId)

  useEffect(() => {
    if (!launchTime) return
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - launchTime) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [launchTime])

  useEffect(() => {
    if (status.data?.status === 'complete' && pollingRunId) {
      onLaunched(pollingRunId)
    }
  }, [status.data?.status, pollingRunId, onLaunched])

  async function handleLaunch() {
    const result = await launch.mutateAsync(launchRequest)
    setPollingRunId(result.run_id)
    setLaunchTime(Date.now())
    setElapsed(0)
  }

  function handleTryAgain() {
    setPollingRunId(null)
    setLaunchTime(null)
    setElapsed(0)
  }

  const pollStatus = status.data?.status
  const isPolling = !!pollingRunId && pollStatus !== 'complete'
  const buttonDisabled = launch.isPending || (!!pollingRunId && pollStatus !== 'failed')

  return (
    <Panel title="Launch">
      <div className="flex flex-col gap-4">
        <Button variant="primary" onClick={() => void handleLaunch()} disabled={buttonDisabled}>
          {launch.isPending ? 'Launching…' : 'Launch Backtest'}
        </Button>

        {isPolling && pollStatus === 'queued' && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            <span className="h-2 w-2 rounded-full bg-text-disabled" />
            <span className="font-mono text-text-secondary">Queued…</span>
          </div>
        )}

        {isPolling && pollStatus === 'running' && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-info" />
            <span className="font-mono text-text-secondary">Running… {elapsed}s</span>
          </div>
        )}

        {isPolling && pollStatus === 'failed' && (
          <div className="flex flex-col gap-2">
            <ErrorState error={{ message: status.data?.error ?? 'Backtest failed' }} compact />
            <Button variant="outline" size="sm" onClick={handleTryAgain}>
              Try again
            </Button>
          </div>
        )}

        {isPolling && (pollStatus === 'queued' || pollStatus === 'running') && (
          <div className="flex flex-col gap-1 font-mono text-xs text-text-secondary">
            <p>Asset: {launchRequest.asset?.toUpperCase()}</p>
            <p>Strategy: {launchRequest.strategy}</p>
            <p>Sizing: {launchRequest.sizing_method ?? 'fixed_notional'}</p>
          </div>
        )}
      </div>
    </Panel>
  )
}
