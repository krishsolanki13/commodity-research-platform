import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { z } from 'zod'

export function useUrlState<T extends z.ZodTypeAny>(
  schema: T,
  defaults: z.infer<T>
): [z.infer<T>, (update: Partial<z.infer<T>>) => void] {
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
    (update: Partial<z.infer<T>>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          Object.entries(update).forEach(([key, value]) => {
            if (value === undefined || value === null) {
              next.delete(key)
            } else {
              next.set(key, String(value))
            }
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
