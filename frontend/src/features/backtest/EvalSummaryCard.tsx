/**
 * EvalSummaryCard — signal evaluation context before backtest launch.
 * Pure presentation; all data arrives as props.
 */
import { AlertTriangle } from 'lucide-react'
import { EmptyState } from '@/components/layout/EmptyState'
import { MetricStat } from '@/components/data/MetricStat'
import { ICDecayChart } from '@/components/charts/ICDecayChart'
import { Panel } from '@/ui/Panel'
import { fmt } from '@/lib/fmt'
import type { components } from '@/api/schema'

type SignalEvaluationData = components['schemas']['SignalEvaluationData']

interface EvalSummaryCardProps {
  evaluation: SignalEvaluationData | null
  evalOverride: boolean
  asset: string
  strategy: string
}

export function EvalSummaryCard({
  evaluation,
  evalOverride,
  asset,
  strategy,
}: EvalSummaryCardProps) {
  if (evalOverride) {
    return (
      <Panel title="Signal Evaluation">
        <EmptyState
          icon={AlertTriangle}
          title="IC Gate override"
          body="This backtest will launch without a signal evaluation. The override will be recorded in the run metadata."
        />
      </Panel>
    )
  }

  if (evaluation === null) {
    return (
      <Panel title="Signal Evaluation">
        <EmptyState
          title="No evaluation found"
          body="Evaluate the signal in the Research Workbench first."
          action={{
            label: 'Back to Workbench →',
            href: `/research?asset=${asset}&strategy=${strategy}`,
          }}
        />
      </Panel>
    )
  }

  return (
    <Panel title="Signal Evaluation">
      <div className="flex flex-col gap-4">
        <div className="flex justify-around w-full">
          <MetricStat label="IC" value={evaluation.ic} format="ic" />
          <MetricStat label="ICIR" value={evaluation.icir} format="ic" />
          <MetricStat label="TURNOVER" value={evaluation.turnover} format="percent" />
        </div>
        <ICDecayChart decay={evaluation.decay} height={160} />
        <p className="text-xs text-text-secondary">
          Evaluated {fmt.isoDate(evaluation.computed_at)}
        </p>
      </div>
    </Panel>
  )
}
