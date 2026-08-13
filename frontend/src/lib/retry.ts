/**
 * Retry wrapper for API calls that may hit a 404 in a narrow race
 * window after status transitions to complete but before disk writes
 * finish (TD-FEP-PORTFOLIO-RACE).
 *
 * Used by portfolio result hooks. Not for status polling hooks.
 * Backend fix: add "persisting" intermediate status (next backend module).
 */
import { ApiClientError } from '@/api/client'

export async function fetchWithRaceRetry<T>(
  fn: () => Promise<T>,
  maxAttempts = 4,
): Promise<T> {
  const delays = [1000, 3000, 6000, 10000]
  for (let i = 0; i < maxAttempts; i++) {
    try {
      return await fn()
    } catch (err) {
      const is404 = err instanceof ApiClientError && err.apiError.status === 404
      if (is404 && i < maxAttempts - 1) {
        await new Promise((r) => setTimeout(r, delays[i] ?? 10000))
        continue
      }
      throw err
    }
  }
  throw new Error('unreachable')
}
