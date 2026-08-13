import type { components } from '@/api/schema'
import { cn } from '@/lib/cn'
import { fmt } from '@/lib/fmt'

type CompareRunSummary = components['schemas']['CompareRunSummary']

interface MetricRowDef {
  key: string
  label: string
  format: 'ratio' | 'percent' | 'drawdown' | 'compactUsd' | 'integer'
  higherIsBetter: boolean
}

const DEFAULT_METRICS: MetricRowDef[] = [
  { key: 'sharpe', label: 'Sharpe', format: 'ratio', higherIsBetter: true },
  { key: 'sortino', label: 'Sortino', format: 'ratio', higherIsBetter: true },
  { key: 'calmar', label: 'Calmar', format: 'ratio', higherIsBetter: true },
  { key: 'total_return', label: 'Total Return', format: 'percent', higherIsBetter: true },
  { key: 'cagr', label: 'CAGR', format: 'percent', higherIsBetter: true },
  { key: 'max_drawdown', label: 'Max Drawdown', format: 'drawdown', higherIsBetter: true },
  { key: 'win_rate', label: 'Win Rate', format: 'percent', higherIsBetter: true },
  { key: 'profit_factor', label: 'Profit Factor', format: 'ratio', higherIsBetter: true },
]

function deltaColor(higherIsBetter: boolean, delta: number): string {
  const isImprovement = higherIsBetter ? delta > 0 : delta < 0
  return isImprovement ? 'var(--text-gain)' : 'var(--text-loss)'
}

function formatMetricValue(format: MetricRowDef['format'], value: number | null): string {
  if (value === null) return '-'
  switch (format) {
    case 'ratio':
      return fmt.ratio(value)
    case 'percent':
      return fmt.percent(value)
    case 'drawdown':
      return fmt.drawdown(value)
    case 'compactUsd':
      return fmt.compactUsd(value)
    case 'integer':
      return Math.round(value).toString()
  }
}

function formatDelta(format: MetricRowDef['format'], delta: number): string {
  const abs = Math.abs(delta)
  let body: string
  switch (format) {
    case 'ratio':
      body = abs.toFixed(2)
      break
    case 'percent':
    case 'drawdown':
      body = `${(abs * 100).toFixed(2)}%`
      break
    case 'compactUsd':
      body = fmt.compactUsd(abs).replace(/^[+$\-\u2212-]*/, '')
      break
    case 'integer':
      body = Math.round(abs).toString()
      break
  }
  const sign = delta > 0 ? '+' : delta < 0 ? '-' : '+'
  return `${sign}${body}`
}

interface MetricDeltaTableProps {
  runs: CompareRunSummary[]
  metrics?: MetricRowDef[]
  baseRunId?: string
  className?: string
}

function columnName(run: CompareRunSummary): string {
  return `${run.asset.toUpperCase()} \u00b7 ${run.strategy}`
}

export function MetricDeltaTable({
  runs,
  metrics = DEFAULT_METRICS,
  baseRunId,
  className,
}: MetricDeltaTableProps) {
  const resolvedBaseId = baseRunId ?? runs[0]?.run_id
  const baseRun = runs.find((r) => r.run_id === resolvedBaseId) ?? runs[0]

  return (
    <div className={cn('overflow-hidden rounded border border-border-default', className)}>
      <table className="w-full table-fixed border-collapse text-sm">
        <thead>
          <tr>
            <th className="border-b border-border-default px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
              METRIC
            </th>
            {runs.map((run) => {
              const label = columnName(run)
              return (
                <th
                  key={run.run_id}
                  className="border-b border-border-default px-3 py-2 text-right font-mono text-xs font-medium text-text-secondary"
                >
                  {label}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric.key} className="border-b border-border-default">
              <td className="px-3 py-2 text-xs text-text-secondary">{metric.label}</td>
              {runs.map((run) => {
                const raw = run.metrics[metric.key]
                const value = raw === undefined ? null : raw
                const isBase = run.run_id === resolvedBaseId
                const baseRaw = baseRun?.metrics[metric.key]
                const baseValue = baseRaw === undefined ? null : baseRaw
                let delta: number | null = null
                if (!isBase && value !== null && baseValue !== null) {
                  delta = value - baseValue
                }

                return (
                  <td key={run.run_id} className="px-3 py-2 text-right font-mono">
                    <div>{formatMetricValue(metric.format, value)}</div>
                    {delta !== null && (
                      <span
                        className="block text-xs"
                        style={{ color: deltaColor(metric.higherIsBetter, delta) }}
                      >
                        {formatDelta(metric.format, delta)}
                      </span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
