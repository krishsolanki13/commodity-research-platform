import { Combobox } from '@/ui/Combobox'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

interface AssetSelectorProps {
  value: string | null
  onChange: (value: string) => void
  assets: AssetMetadata[]
  multiple?: boolean
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

export function AssetSelector({
  value,
  onChange,
  assets,
  disabled,
  className,
  'aria-label': ariaLabel,
}: AssetSelectorProps) {
  const options = assets.map((a) => ({
    value: a.name,
    label: a.display_name,
    meta: `${a.ticker_continuous} · ${a.exchange}`,
  }))

  return (
    <Combobox
      options={options}
      value={value}
      onChange={onChange}
      placeholder="Select an asset..."
      disabled={disabled}
      className={className}
      aria-label={ariaLabel}
    />
  )
}
