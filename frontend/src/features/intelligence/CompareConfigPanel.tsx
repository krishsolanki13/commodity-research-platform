import { z } from 'zod'
import { ASSET_NAMES, useCurveAvailableAssets } from '@/api/hooks'
import { cn } from '@/lib/cn'
import { displayName } from '@/lib/commodity'
import { useUrlState } from '@/lib/useUrlState'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/ui/select'
import { Separator } from '@/ui/separator'

export const compareSchema = z.object({
  assets: z.string().optional(),
  n_contracts: z.coerce.number().int().min(1).max(6).default(4),
})

export function CompareConfigPanel() {
  const [urlState, setUrlState] = useUrlState(compareSchema, { n_contracts: 4 })
  const { data: available, isLoading } = useCurveAvailableAssets()
  const assetList = (urlState.assets ?? '').split(',').filter(Boolean).slice(0, 4)
  const availableAssets = available?.assets ?? ASSET_NAMES

  function toggleAsset(name: string) {
    const updated = assetList.includes(name)
      ? assetList.filter((asset) => asset !== name)
      : assetList.length >= 4
        ? assetList
        : [...assetList, name]
    setUrlState({ assets: updated.length > 0 ? updated.join(',') : undefined })
  }

  return (
    <div className="w-64 flex shrink-0 flex-col gap-4 border-r border-border-default p-4">
      <h2 className="text-sm font-semibold text-text-emphasis">Select Assets (max 4)</h2>

      <div className="flex flex-col gap-2" aria-busy={isLoading}>
        {availableAssets.map((name) => {
          const selected = assetList.includes(name)
          const maxReached = !selected && assetList.length >= 4

          return (
            <label
              key={name}
              className={cn(
                'flex items-center gap-2 text-sm',
                maxReached ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'
              )}
            >
              <input
                type="checkbox"
                checked={selected}
                onChange={() => toggleAsset(name)}
                disabled={maxReached}
                aria-label={`Compare ${displayName(name)}`}
                className="h-4 w-4"
                style={{ accentColor: 'var(--accent)' }}
              />
              <span className={selected ? 'text-text-emphasis' : 'text-text-secondary'}>
                {displayName(name)}
              </span>
            </label>
          )
        })}
      </div>

      <Separator />

      <div className="gap-1.5 flex flex-col">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Contracts
        </span>
        <Select
          value={String(urlState.n_contracts)}
          onValueChange={(value) => setUrlState({ n_contracts: Number(value) })}
        >
          <SelectTrigger aria-label="Number of contracts to compare">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[2, 3, 4, 5, 6].map((number) => (
              <SelectItem key={number} value={String(number)}>
                {number} contracts
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
