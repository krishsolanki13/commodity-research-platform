/**
 * useChartTheme() — derives an ECharts theme object from the active design token set.
 *
 * Reads CSS custom properties from document.documentElement at call time via
 * getComputedStyle(). Depends on useWorkspace().theme so it re-derives when the
 * user toggles dark/light mode.
 *
 * CRITICAL: No hex literals in this file (except resolveCssVar fallbacks, which
 * fire only when a token is missing). All color values come from CSS custom
 * properties. The resolved color strings appear only in the returned
 * object — they are runtime values, not source-level literals.
 */
import { useMemo } from 'react'
import { useWorkspace } from '@/stores/workspace'

/**
 * Resolve a CSS custom property to a concrete color string for ECharts.
 * ECharts cannot consume var(--x) — it falls back to #000000.
 * Fallbacks are last-resort only when the token is unavailable (SSR / missing).
 */
export function resolveCssVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

export interface EChartsTheme {
  backgroundColor: string
  textStyle: {
    color: string
    fontFamily: string
    fontSize: number
  }
  axisPointer: {
    lineStyle: { color: string; type: 'dashed' }
    crossStyle: { color: string }
    label: { backgroundColor: string; color: string; fontFamily: string }
  }
  grid: { borderColor: string }
  tooltip: {
    backgroundColor: string
    borderColor: string
    textStyle: { color: string; fontFamily: string; fontSize: number }
  }
  seriesPalette: string[] // 6 colors from --series-1..6 tokens
  gain: string // resolved --gain-500
  loss: string // resolved --loss-500
  gainFill: string // resolved --gain-900a
  lossFill: string // resolved --loss-900a
  amber: string // resolved --amber-500
  gridlineColor: string // --gray-800 at ~60% opacity (hex alpha)
  secondaryText: string // resolved --text-secondary
  monoFont: string // resolved --font-mono
  icStrong: string // resolved --ic-strong
  icWeak: string // resolved --ic-weak
  icNoise: string // resolved --ic-noise
}

export function useChartTheme(): EChartsTheme {
  const { theme } = useWorkspace() // triggers re-derivation on dark/light toggle

  return useMemo(() => {
    // theme is the memoization key: CSS vars change with data-theme, so we must
    // re-read getComputedStyle when the workspace theme toggles.
    void theme
    const s = getComputedStyle(document.documentElement)
    const get = (name: string) => s.getPropertyValue(name).trim()

    return {
      backgroundColor: 'transparent',
      textStyle: {
        color: get('--text-secondary'),
        fontFamily: get('--font-mono'),
        fontSize: 11,
      },
      axisPointer: {
        lineStyle: { color: get('--gray-500'), type: 'dashed' },
        crossStyle: { color: get('--gray-500') },
        label: {
          backgroundColor: get('--bg-raised'),
          color: get('--text-primary'),
          fontFamily: get('--font-mono'),
        },
      },
      grid: { borderColor: get('--border-default') },
      tooltip: {
        backgroundColor: get('--bg-raised'),
        borderColor: get('--border-strong'),
        textStyle: {
          color: get('--text-primary'),
          fontFamily: get('--font-mono'),
          fontSize: 12,
        },
      },
      seriesPalette: [1, 2, 3, 4, 5, 6].map((i) => get(`--series-${i}`)),
      gain: get('--gain-500'),
      loss: get('--loss-500'),
      gainFill: get('--gain-900a'),
      lossFill: get('--loss-900a'),
      amber: get('--amber-500'),
      // --gray-800 resolves to a hex color; appending '99' gives ~60% opacity alpha
      gridlineColor: `${get('--gray-800')}99`,
      secondaryText: get('--text-secondary'),
      monoFont: get('--font-mono'),
      icStrong: get('--ic-strong'),
      icWeak: get('--ic-weak'),
      icNoise: get('--ic-noise'),
    }
  }, [theme]) // 'theme' string is the memoization dependency
}
