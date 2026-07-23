import { useEffect, useState } from 'react'
import { usePortfolioLaunch, usePortfolioStatus } from '@/api/hooks'
import { ErrorState } from '@/components/layout/ErrorState'
import { Button } from '@/ui/button'
import type { components } from '@/api/schema'

type PortfolioLaunchRequest = components['schemas']['PortfolioLaunchRequest']

interface PortfolioLaunchPanelProps {
  strategy: string
  params: Record<string, unknown>
  sizingMethod: 'fixed_notional' | 'volatility_scaled'
  initialCapital: number
  onLaunched: (runId: string) => void
}

export function PortfolioLaunchPanel({
  strategy,
  params,
  sizingMethod,
  initialCapital,
  onLaunched,
}: PortfolioLaunchPanelProps) {
  const [pollingRunId, setPollingRunId] = useState<string | null>(null)
  const [launchTime, setLaunchTime] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState(0)

  const launch = usePortfolioLaunch()
  const status = usePortfolioStatus(pollingRunId)

  useEffect(() => {
    if (!launchTime) return
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - launchTime) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [launchTime])

  useEffect(() => {
    if (status.data?.status === 'complete' && pollingRunId) {
      // Prefer a clean artifact id from status when present; else strip poll_ prefix
      const statusRunId = status.data.run_id
      const artifactId = (statusRunId && !statusRunId.startsWith('poll_')
        ? statusRunId
        : pollingRunId
      ).replace(/^poll_/, '')
      onLaunched(artifactId)
    }
  }, [status.data?.status, status.data?.run_id, pollingRunId, onLaunched])

  async function handleLaunch() {
    const request: PortfolioLaunchRequest = {
      strategy,
      params,
      initial_capital_per_asset: initialCapital,
      commission_per_trade: 5,
      slippage_ticks: 1,
      sizing_method: sizingMethod,
      notional_usd: 100_000,
      signal_threshold: 0,
    }
    const result = await launch.mutateAsync(request)
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
    <div className="flex flex-col gap-3">
      <Button
        variant="primary"
        onClick={() => void handleLaunch()}
        disabled={buttonDisabled}
        className="w-full"
      >
        {launch.isPending ? 'Launching…' : 'Launch Portfolio Backtest'}
      </Button>

      {isPolling && pollStatus === 'queued' && (
        <p className="font-mono text-xs text-text-secondary">Queued…</p>
      )}
      {isPolling && pollStatus === 'running' && (
        <p className="font-mono text-xs text-text-secondary">Running… {elapsed}s</p>
      )}
      {isPolling && pollStatus === 'failed' && (
        <div className="flex flex-col gap-2">
          <ErrorState error={{ message: status.data?.error ?? 'Portfolio run failed' }} compact />
          <Button variant="outline" size="sm" onClick={handleTryAgain}>
            Try again
          </Button>
        </div>
      )}

      <p className="font-mono text-xs text-text-secondary">
        Runs all 6 assets with {strategy} strategy. ~30–60s typical.
      </p>
    </div>
  )
}
