import { z } from 'zod'
import { DateScrubber } from '@/components/inputs/DateScrubber'
import { useCurveHistory } from '@/api/hooks/useCurveHistory'
import { useUrlState } from '@/lib/useUrlState'

// Minimal schema — reads only the fields this component needs from the URL.
// setUrlState merges URL params; other fields (n_contracts, lookback) are untouched.
const schema = z.object({
  asset: z.string().optional(),
  observation_date: z.string().optional(),
})

const defaults = {
  asset: undefined as string | undefined,
  observation_date: undefined as string | undefined,
}

export function CurveDateControl() {
  const today = new Date().toISOString().slice(0, 10)

  // All hooks called unconditionally — early return is below
  const [{ asset, observation_date }, setUrlState] = useUrlState(schema, defaults)

  const { data: history, isLoading: historyLoading } = useCurveHistory(
    asset ?? '',
    '2023-01-01',
    today,
    2
  )

  if (!asset) return null

  const minDate = history?.snapshots[0]?.observation_date
  const maxDate = today

  return (
    <div className="flex items-center gap-3">
      <span className="font-mono text-xs text-text-secondary">Observation date:</span>
      <DateScrubber
        value={observation_date ?? null}
        onChange={(date) => setUrlState({ observation_date: date ?? undefined })}
        minDate={minDate}
        maxDate={maxDate}
        disabled={historyLoading}
      />
      {observation_date && (
        <span className="font-mono text-xs text-text-disabled">{observation_date}</span>
      )}
    </div>
  )
}
