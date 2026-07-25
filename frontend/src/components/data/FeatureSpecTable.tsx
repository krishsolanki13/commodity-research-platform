import type { components } from '@/api/schema'
import { fmt } from '@/lib/fmt'
import { cn } from '@/lib/cn'

type FeatureSpecResponse = components['schemas']['FeatureSpecResponse']

interface FeatureSpecTableProps {
  specs: FeatureSpecResponse[]
  className?: string
}

export function FeatureSpecTable({ specs, className }: FeatureSpecTableProps) {
  if (!specs || specs.length === 0) return null
  return (
    <table
      role="grid"
      className={cn('w-full table-fixed border-collapse text-sm', className)}
    >
      <thead className="bg-bg-raised">
        <tr>
          {['INDICATOR', 'PARAMS', 'COLUMN', 'COMPUTED'].map((h) => (
            <th
              key={h}
              className="px-3 py-2 text-left text-xs font-medium
                uppercase tracking-wider text-text-secondary"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {specs.map((spec) => (
          <tr
            key={spec.column_name}
            className="border-b border-border-default"
          >
            <td className="px-3 py-2 font-mono text-xs text-text-primary">
              {spec.indicator_name}
            </td>
            <td className="px-3 py-2 font-mono text-xs text-text-secondary">
              {JSON.stringify(spec.params)}
            </td>
            <td className="px-3 py-2 font-mono text-xs text-accent">
              {spec.column_name}
            </td>
            <td className="px-3 py-2 font-mono text-xs text-text-secondary">
              {spec.computed_at ? fmt.isoDate(spec.computed_at) : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
