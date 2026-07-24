import { useNavigate } from 'react-router-dom'
import { ICGateStrip } from '@/components/data/ICGateStrip'
import type { components } from '@/api/schema'

type SignalEvaluationData = components['schemas']['SignalEvaluationData']

/** R-Q3: flat props - not a bundled urlState object. */
interface WorkbenchICGateStripProps {
  evaluation: SignalEvaluationData | null
  evaluating: boolean
  asset: string
  strategy: string
  paramsJson: string
}

export function WorkbenchICGateStrip({
  evaluation,
  evaluating,
  asset,
  strategy,
  paramsJson,
}: WorkbenchICGateStripProps) {
  const navigate = useNavigate()

  // PATH A — Configure backtest: thread evaluation JSON only (never evalOverride)
  const handleConfigureBacktest = () => {
    const params = new URLSearchParams({
      asset,
      strategy,
      params: paramsJson,
    })
    if (evaluation) {
      params.set('evaluation', JSON.stringify(evaluation))
    }
    params.delete('evalOverride')
    void navigate(`/backtest/new?${params.toString()}`)
  }

  // PATH B — Backtest without evaluation: evalOverride=1 only (never evaluation=)
  const handleOverride = () => {
    const params = new URLSearchParams({
      asset,
      strategy,
      params: paramsJson,
      evalOverride: '1',
    })
    params.delete('evaluation')
    void navigate(`/backtest/new?${params.toString()}`)
  }

  return (
    <ICGateStrip
      evaluation={evaluation}
      loading={evaluating}
      onConfigureBacktest={handleConfigureBacktest}
      onOverride={handleOverride}
    />
  )
}
