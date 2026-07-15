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

  const handleConfigureBacktest = () => {
    const url = `/backtest/new?asset=${encodeURIComponent(asset)}&strategy=${encodeURIComponent(strategy)}&params=${encodeURIComponent(paramsJson)}`
    void navigate(url)
  }

  const handleOverride = () => {
    const url = `/backtest/new?asset=${encodeURIComponent(asset)}&strategy=${encodeURIComponent(strategy)}&params=${encodeURIComponent(paramsJson)}&evalOverride=1`
    void navigate(url)
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
