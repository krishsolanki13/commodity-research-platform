export function safeJsonParse<T>(s: string | undefined, fallback: T): T {
    if (!s) return fallback
    try { return JSON.parse(s) as T } catch { return fallback }
  }
