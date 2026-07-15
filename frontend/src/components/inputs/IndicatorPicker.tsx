import { useMemo, useState, useRef } from 'react'
import { Lock, X } from 'lucide-react'
import { cn } from '@/lib/cn'
import { ParamForm } from '@/components/inputs/ParamForm'
import type { components } from '@/api/schema'

type IndicatorMeta = components['schemas']['IndicatorMeta']
type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']

interface IndicatorPickerProps {
  catalog: IndicatorMeta[]
  selected: FeatureSpecRequest[]
  onChange: (selected: FeatureSpecRequest[]) => void
  requiredSpecs?: FeatureSpecRequest[]
  className?: string
}

function resolveColumnName(template: string, params: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const value = params[key]
    if (value === undefined || value === null) return key
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return String(value)
    }
    return key
  })
}

function isDuplicate(spec: FeatureSpecRequest, existing: FeatureSpecRequest[]): boolean {
  return existing.some(
    (e) => e.name === spec.name && JSON.stringify(e.params) === JSON.stringify(spec.params)
  )
}

function defaultParams(indicator: IndicatorMeta): Record<string, unknown> {
  return Object.fromEntries(indicator.params_schema.map((p) => [p.name, p.default]))
}

export function IndicatorPicker({
  catalog,
  selected,
  onChange,
  requiredSpecs = [],
  className,
}: IndicatorPickerProps) {
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [draftParams, setDraftParams] = useState<Record<string, unknown>>({})
  const draftParamsRef = useRef(draftParams)
  draftParamsRef.current = draftParams

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return catalog
    return catalog.filter(
      (i) =>
        i.name.toLowerCase().includes(q) || i.display_name.toLowerCase().includes(q)
    )
  }, [catalog, search])

  const grouped = useMemo(() => {
    const map = new Map<string, IndicatorMeta[]>()
    for (const indicator of filtered) {
      const list = map.get(indicator.category) ?? []
      list.push(indicator)
      map.set(indicator.category, list)
    }
    return map
  }, [filtered])

  const displaySpecs = useMemo(() => {
    const merged = [...requiredSpecs, ...selected]
    const unique: FeatureSpecRequest[] = []
    for (const spec of merged) {
      if (!isDuplicate(spec, unique)) unique.push(spec)
    }
    return unique
  }, [requiredSpecs, selected])

  function isRequired(spec: FeatureSpecRequest): boolean {
    return isDuplicate(spec, requiredSpecs)
  }

  function findIndicator(name: string): IndicatorMeta | undefined {
    return catalog.find((i) => i.name === name)
  }

  function handleIndicatorClick(indicator: IndicatorMeta) {
    if (expanded === indicator.name) {
      setExpanded(null)
      return
    }
    setExpanded(indicator.name)
    setDraftParams(defaultParams(indicator))
  }

  function handleAdd(indicator: IndicatorMeta) {
    const spec: FeatureSpecRequest = {
      name: indicator.name,
      params: { ...draftParamsRef.current },
    }
    const existing = [...requiredSpecs, ...selected]
    if (isDuplicate(spec, existing)) return
    onChange([...selected, spec])
    setExpanded(null)
  }

  function handleRemove(spec: FeatureSpecRequest) {
    onChange(
      selected.filter(
        (s) =>
          !(s.name === spec.name && JSON.stringify(s.params) === JSON.stringify(spec.params))
      )
    )
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search indicators..."
        aria-label="Search indicators"
        className={cn(
          'h-[var(--input-height)] rounded-sm border border-border-strong bg-bg-app',
          'px-3 text-sm text-text-primary placeholder:text-text-secondary',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
      />

      {displaySpecs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {displaySpecs.map((spec) => {
            const indicator = findIndicator(spec.name)
            const label = indicator
              ? resolveColumnName(indicator.column_name_template, spec.params)
              : spec.name
            const locked = isRequired(spec)

            return (
              <span
                key={`${spec.name}-${JSON.stringify(spec.params)}`}
                className={cn(
                  'inline-flex items-center gap-1 rounded-sm border border-border-default',
                  'bg-bg-raised px-2 py-1 font-mono text-xs text-text-primary'
                )}
              >
                {locked && (
                  <Lock size={12} strokeWidth={1.75} className="text-text-secondary" aria-hidden />
                )}
                {label}
                {!locked && (
                  <button
                    type="button"
                    aria-label={`Remove ${label}`}
                    onClick={() => handleRemove(spec)}
                    className="text-text-secondary hover:text-text-primary"
                  >
                    <X size={12} strokeWidth={1.75} />
                  </button>
                )}
              </span>
            )
          })}
        </div>
      )}

      <div className="flex flex-col gap-4">
        {[...grouped.entries()].map(([category, indicators]) => (
          <div key={category}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-secondary">
              {category}
            </p>
            <div className="flex flex-col gap-1">
              {indicators.map((indicator) => (
                <div key={indicator.name}>
                  <button
                    type="button"
                    onClick={() => handleIndicatorClick(indicator)}
                    className={cn(
                      'w-full rounded-sm px-2 py-1.5 text-left text-sm',
                      'hover:bg-bg-hover',
                      expanded === indicator.name && 'bg-bg-selected'
                    )}
                  >
                    {indicator.display_name}
                  </button>
                  {expanded === indicator.name && (
                    <div className="mt-2 rounded-sm border border-border-default p-3">
                      <ParamForm
                        schema={indicator.params_schema}
                        values={draftParams}
                        onChange={(next) => {
                          draftParamsRef.current = next
                          setDraftParams(next)
                        }}
                        layout="stack"
                      />
                      <button
                        type="button"
                        onClick={() => handleAdd(indicator)}
                        className={cn(
                          'mt-3 rounded-sm border border-border-strong px-3 py-1',
                          'text-xs text-text-primary hover:bg-bg-hover'
                        )}
                      >
                        Add indicator
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export { resolveColumnName, isDuplicate }
