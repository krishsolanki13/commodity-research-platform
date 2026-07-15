import { UniverseStatsBar } from '@/features/market/UniverseStatsBar'
import { UniverseTablePanel } from '@/features/market/UniverseTablePanel'
import { ReturnComparisonPanel } from '@/features/market/ReturnComparisonPanel'
import { VolatilityPanel } from '@/features/market/VolatilityPanel'
import { useUrlState } from '@/lib/useUrlState'
import { z } from 'zod'

const rangeSchema = z.object({
  range: z.enum(['1M', '3M', '6M', '1Y', '3Y', '5Y', 'MAX']).default('1Y'),
})

export default function MarketOverviewScreen() {
  const [{ range }] = useUrlState(rangeSchema, { range: '1Y' })

  return (
    <div className="flex flex-col gap-6 p-6">
      <UniverseStatsBar />
      <UniverseTablePanel />
      <div className="grid grid-cols-2 gap-6">
        <ReturnComparisonPanel range={range} />
        <VolatilityPanel />
      </div>
    </div>
  )
}
