import { Panel } from '@/ui/Panel'
import { fmt } from '@/lib/fmt'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

interface AssetMetadataPanelProps {
  metadata: AssetMetadata | null
}

export function AssetMetadataPanel({ metadata }: AssetMetadataPanelProps) {
  if (!metadata) return null

  const rows = [
    { label: 'CONTRACT MULTIPLIER', value: `${metadata.contract_multiplier} ${metadata.unit}` },
    { label: 'TICK SIZE', value: fmt.price(metadata.tick_size, metadata.name) },
    { label: 'TICK VALUE', value: `$${metadata.tick_value.toFixed(2)}` },
    { label: 'EXCHANGE', value: metadata.exchange },
    { label: 'UNIT', value: metadata.unit },
  ]

  return (
    <Panel title="Contract Specs">
      <table className="w-full table-fixed text-xs">
        <tbody>
          {rows.map(({ label, value }) => (
            <tr key={label} className="border-b border-border-default last:border-b-0">
              <td className="py-1.5 pr-4 text-text-secondary">{label}</td>
              <td className="py-1.5 font-mono text-text-primary">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  )
}
