import { useEffect, useMemo, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { cn } from '@/lib/cn'
import { NumberInput } from '@/ui/NumberInput'
import { Input } from '@/ui/input'
import { Switch } from '@/ui/switch'
import type { components } from '@/api/schema'

type ParamSpec = components['schemas']['ParamSpec']

interface ParamFormProps {
  schema: ParamSpec[]
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
  errors?: Record<string, string>
  layout?: 'grid' | 'stack'
  className?: string
}

export function ParamForm({
  schema,
  values,
  onChange,
  layout = 'stack',
  className,
}: ParamFormProps) {
  const zodSchema = useMemo(
    () =>
      z.object(
        Object.fromEntries(
          schema.map((p) => [
            p.name,
            p.kind === 'int'
              ? z.coerce
                  .number()
                  .int()
                  .min(p.min ?? -Infinity)
                  .max(p.max ?? Infinity)
              : p.kind === 'float'
                ? z.coerce
                    .number()
                    .min(p.min ?? -Infinity)
                    .max(p.max ?? Infinity)
                : p.kind === 'bool'
                  ? z.boolean()
                  : z.string(),
          ])
        )
      ),
    [schema]
  )

  const form = useForm({
    resolver: zodResolver(zodSchema),
    defaultValues: values,
    mode: 'onBlur',
  })

  // Subscribe to formState so isValid updates after blur validation (RHF proxy)
  const { isValid, errors } = form.formState
  const [watchTick, setWatchTick] = useState(0)

  useEffect(() => {
    const subscription = form.watch(() => {
      setWatchTick((t) => t + 1)
    })
    return () => subscription.unsubscribe()
  }, [form])

  useEffect(() => {
    if (!isValid) return
    const watchedValues: Record<string, unknown> = form.getValues()
    if (JSON.stringify(watchedValues) === JSON.stringify(values)) return
    onChange(watchedValues)
  }, [form, onChange, values, isValid, watchTick])

  useEffect(() => {
    form.reset(values)
    // form intentionally omitted: useForm() returns a stable object reference (RHF guarantee)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values])

  return (
    <div
      className={cn(
        layout === 'grid' ? 'grid grid-cols-2 gap-4' : 'flex flex-col gap-4',
        className
      )}
    >
      {schema.map((p) => {
        const fieldError = errors[p.name]
        const errorMessage = fieldError?.message ? String(fieldError.message) : undefined

        return (
          <div key={p.name} className="flex flex-col gap-1">
            <div className="flex items-center gap-1">
              <label htmlFor={p.name} className="text-sm text-text-secondary">
                {p.name}
              </label>
              {p.unit && <span className="text-xs text-text-secondary">({p.unit})</span>}
              <button
                type="button"
                onClick={() => form.setValue(p.name, p.default, { shouldValidate: true })}
                className="ml-1 text-xs text-text-secondary hover:text-text-primary"
                aria-label={`Reset ${p.name} to default`}
              >
                ↺
              </button>
            </div>

            {p.kind === 'int' || p.kind === 'float' ? (
              <Controller
                name={p.name}
                control={form.control}
                render={({ field }) => (
                  <NumberInput
                    id={p.name}
                    aria-label={p.description ?? p.name}
                    value={(field.value as number | '' | undefined) ?? ''}
                    onChange={(v) => {
                      field.onChange(v)
                      void field.onBlur()
                    }}
                    min={p.min ?? undefined}
                    max={p.max ?? undefined}
                    step={p.kind === 'float' ? 0.01 : 1}
                    unit={p.unit ?? undefined}
                  />
                )}
              />
            ) : p.kind === 'bool' ? (
              <Controller
                name={p.name}
                control={form.control}
                render={({ field }) => (
                  <Switch checked={!!field.value} onCheckedChange={field.onChange} />
                )}
              />
            ) : (
              <Input id={p.name} {...form.register(p.name)} />
            )}

            {errorMessage && <p className="text-xs text-crit">{errorMessage}</p>}
          </div>
        )
      })}
    </div>
  )
}
