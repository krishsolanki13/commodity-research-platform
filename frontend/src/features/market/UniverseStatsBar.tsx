import { useState } from 'react'
import { useAssets } from '@/api/hooks/useAssets'
import { useDataStatus } from '@/api/hooks/useDataStatus'
import { useIngestMutation } from '@/api/hooks/useIngestMutation'
import { MetricGrid } from '@/components/data/MetricGrid'
import type { MetricStatProps } from '@/components/data/MetricStat'
import { Button } from '@/ui/button'
import { RANGE_PRESETS } from '@/lib/date-range'
import type { RangePreset } from '@/lib/date-range'
import { useUrlState } from '@/lib/useUrlState'
import { z } from 'zod'
import { cn } from '@/lib/cn'

const rangeSchema = z.object({
  range: z.enum(['1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX']).default('1Y'),
})

export function UniverseStatsBar() {
  const { data: universe, isLoading: universeLoading } = useAssets()
  const { data: status } = useDataStatus()
  const ingest = useIngestMutation()
  const [{ range }, setUrlState] = useUrlState(rangeSchema, { range: '1Y' })
  // Backend may return last_ingestion: null — stamp local time after a successful re-ingest.
  const [lastIngestedAt, setLastIngestedAt] = useState<Date | null>(null)

  const lastIngestionDisplay = lastIngestedAt
    ? lastIngestedAt.toLocaleTimeString()
    : (universe?.last_ingestion ?? '—')

  const metrics: MetricStatProps[] = [
    {
      label: 'ASSETS TRACKED',
      value: universe?.assets.length ?? null,
      format: 'integer',
      tone: 'neutral',
    },
    {
      label: 'LAST INGESTION',
      value: lastIngestionDisplay,
      format: 'raw',
      tone: 'neutral',
      hint: lastIngestedAt
        ? `Ingested at ${lastIngestedAt.toLocaleString()}`
        : universe?.last_ingestion
          ? `Last ingested ${universe.last_ingestion}`
          : 'Never ingested',
    },
    {
      label: 'FLAGGED ANOMALIES',
      value: status?.total_flags ?? null,
      format: 'integer',
      tone: 'neutral',
    },
    {
      label: 'RUNS TOTAL',
      value: universe?.total_runs ?? null,
      format: 'integer',
      tone: 'neutral',
    },
  ]

  function handleRange(r: RangePreset) {
    setUrlState({ range: r })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-emphasis">Market Overview</h1>
        <div className="flex items-center gap-3">
          <div className="flex overflow-hidden rounded-sm border border-border-strong">
            {RANGE_PRESETS.map((r) => (
              <button
                key={r}
                onClick={() => handleRange(r)}
                aria-pressed={range === r}
                className={cn(
                  'border-r border-border-strong px-2 py-1 font-mono text-xs last:border-r-0',
                  'transition-colors duration-fast',
                  range === r
                    ? 'bg-accent font-medium text-bg-app'
                    : 'bg-bg-app text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                )}
              >
                {r}
              </button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              ingest.mutate(
                { asset: null },
                {
                  onSuccess: () => {
                    setLastIngestedAt(new Date())
                  },
                }
              )
            }
            disabled={ingest.isPending}
          >
            {ingest.isPending ? 'Ingesting…' : 'Re-ingest all'}
          </Button>
          {ingest.isSuccess && (
            <span className="ml-2 text-xs text-text-secondary">
              {ingest.data?.assets_ingested?.length ?? 6} assets ingested
            </span>
          )}
        </div>
      </div>
      <MetricGrid metrics={metrics} loading={universeLoading} />
    </div>
  )
}
