import { useMemo } from 'react'
import { createColumnHelper } from '@tanstack/react-table'
import { DataGrid } from '@/components/data/DataGrid'
import { fmt } from '@/lib/fmt'
import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type FeatureSpecResponse = components['schemas']['FeatureSpecResponse']

interface FeatureSpecTableProps {
  specs: FeatureSpecResponse[]
  className?: string
}

const colHelper = createColumnHelper<FeatureSpecResponse>()

export function FeatureSpecTable({ specs, className }: FeatureSpecTableProps) {
  const columns = useMemo(
    () => [
      colHelper.accessor('indicator_name', {
        header: 'INDICATOR',
        enableSorting: false,
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
      }),
      colHelper.accessor('params', {
        header: 'PARAMS',
        enableSorting: false,
        cell: (info) => (
          <span className="font-mono text-xs">{JSON.stringify(info.getValue())}</span>
        ),
      }),
      colHelper.accessor('column_name', {
        header: 'COLUMN',
        enableSorting: false,
        cell: (info) => <span className="font-mono text-xs text-accent">{info.getValue()}</span>,
      }),
      colHelper.accessor('computed_at', {
        header: 'COMPUTED',
        enableSorting: false,
        cell: (info) => (
          <span className="text-xs text-text-secondary">
            {fmt.isoDate(new Date(info.getValue()))}
          </span>
        ),
      }),
    ],
    []
  )

  return (
    <DataGrid
      columns={columns}
      data={specs}
      getRowId={(row) => row.column_name}
      virtualized={false}
      className={cn(className)}
    />
  )
}
