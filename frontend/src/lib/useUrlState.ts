import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { z } from 'zod'

type NullablePartial<T> = { [K in keyof T]?: T[K] | null }

export function useUrlState<T extends z.ZodTypeAny>(
  schema: T,
  defaults: z.infer<T>
): [z.infer<T>, (update: NullablePartial<z.infer<T>>) => void] {
  const [searchParams, setSearchParams] = useSearchParams()

  const parsed = (() => {
    const raw: Record<string, string> = {}
    searchParams.forEach((value, key) => {
      raw[key] = value
    })
    const result = schema.safeParse(raw)
    return result.success ? (result.data as z.infer<T>) : defaults
  })()

  const setState = useCallback(
    (update: NullablePartial<z.infer<T>>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          Object.entries(update).forEach(([key, value]) => {
            if (value === null) {
              // null = explicit clear: remove the URL param
              next.delete(key)
            } else if (value !== undefined) {
              // defined, non-null = set the URL param
              next.set(key, String(value))
            }
            // undefined = no-op: preserve existing URL param value
          })
          return next
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  return [parsed, setState]
}
