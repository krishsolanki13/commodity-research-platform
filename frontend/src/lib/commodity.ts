/**
 * Shared commodity display utilities.
 * Extracted in F11 to avoid duplication between IntelligenceConfigRail
 * and CompareConfigPanel. All feature components import from here.
 */

export const COMMODITY_DISPLAY_NAMES: Record<string, string> = {
  gold: 'Gold',
  silver: 'Silver',
  copper: 'Copper',
  wti: 'WTI Crude',
  brent: 'Brent Crude',
  natural_gas: 'Natural Gas',
}

export function displayName(asset: string): string {
  return COMMODITY_DISPLAY_NAMES[asset] ?? asset.charAt(0).toUpperCase() + asset.slice(1)
}
