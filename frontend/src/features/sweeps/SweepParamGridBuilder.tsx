// Q8 confirmed: comma-separated text input per param (Option A)
// Validation: ≥2 values required, all must parse as numbers

import { useState, useEffect } from 'react'

interface SweepParamGridBuilderProps {
  paramNames: string[]
  paramTypes: Record<string, 'int' | 'float'>
  onChange: (grid: Record<string, unknown[]>, valid: boolean) => void
}

function parseValues(
  raw: string,
  type: 'int' | 'float',
): { values: unknown[]; error: string | null } {
  const parts = raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

  if (parts.length < 2) {
    return { values: [], error: 'Enter at least 2 comma-separated values' }
  }

  const values = parts.map((s) => {
    return type === 'int' ? parseInt(s, 10) : parseFloat(s)
  })

  if (values.some((v) => isNaN(v as number))) {
    return { values: [], error: 'All values must be valid numbers' }
  }

  if (type === 'int' && values.some((v) => !Number.isInteger(v))) {
    return { values: [], error: 'Integer params require whole numbers' }
  }

  return { values, error: null }
}

function formatParamLabel(name: string): string {
  return name.replace(/_/g, ' ').toUpperCase()
}

export function SweepParamGridBuilder({
  paramNames,
  paramTypes,
  onChange,
}: SweepParamGridBuilderProps) {
  const [rawValues, setRawValues] = useState<Record<string, string>>(
    Object.fromEntries(paramNames.map((n) => [n, ''])),
  )
  const [errors, setErrors] = useState<Record<string, string | null>>(
    Object.fromEntries(paramNames.map((n) => [n, null])),
  )

  // Reset when paramNames changes (strategy switch)
  useEffect(() => {
    setRawValues(Object.fromEntries(paramNames.map((n) => [n, ''])))
    setErrors(Object.fromEntries(paramNames.map((n) => [n, null])))
  }, [paramNames.join(',')])

  function handleChange(param: string, raw: string) {
    const nextRaw = { ...rawValues, [param]: raw }
    setRawValues(nextRaw)

    const nextErrors = { ...errors }
    const grid: Record<string, unknown[]> = {}
    let allValid = true

    for (const p of paramNames) {
      const type = paramTypes[p] ?? 'float'
      const result = parseValues(nextRaw[p] ?? '', type)
      nextErrors[p] = result.error
      grid[p] = result.values
      if (result.error || result.values.length === 0) allValid = false
    }

    setErrors(nextErrors)
    onChange(grid, allValid)
  }

  if (paramNames.length === 0) {
    return (
      <p className="text-xs text-text-secondary">
        Select a strategy to configure parameter ranges.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {paramNames.map((param) => (
        <div key={param} className="flex flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wider text-text-secondary">
            {formatParamLabel(param)}
          </span>
          <span className="text-xs text-text-disabled">
            ({paramTypes[param] ?? 'float'}) — comma-separated values
          </span>
          <input
            type="text"
            placeholder="e.g. 10, 20, 50, 100"
            value={rawValues[param] ?? ''}
            onChange={(e) => handleChange(param, e.target.value)}
            className="w-full rounded border border-border-strong bg-bg-raised px-2 py-1.5 text-sm font-mono text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-1 focus:ring-focus-ring"
          />
          {errors[param] && (
            <p className="mt-0.5 text-xs text-loss">{errors[param]}</p>
          )}
        </div>
      ))}
    </div>
  )
}
