import { Page, expect } from '@playwright/test'

const API_ORIGIN = 'http://localhost:8000'

/**
 * Navigate to a screen with asset + strategy pre-selected via URL params.
 * This matches the pattern used by all existing specs.
 */
export async function gotoWithParams(
  page: Page,
  path: string,
  asset?: string,
  strategy?: string
): Promise<void> {
  const params = new URLSearchParams()
  if (asset) params.set('asset', asset)
  if (strategy) params.set('strategy', strategy)
  const qs = params.toString()
  await page.goto(qs ? `${path}?${qs}` : path)
}

/**
 * Click a strategy button in the Research Workbench StrategyPicker.
 * StrategyPicker renders strategy.display_name as a <button> (not a combobox).
 * Confirmed label for ema_crossover: "EMA Crossover".
 */
export async function clickStrategyButton(page: Page, strategyLabel: string): Promise<void> {
  await page.getByRole('button', { name: strategyLabel }).click()
  await page.waitForTimeout(200)
}

/**
 * Select asset via labeled combobox — for screens that use the dropdown.
 * aria-label differs: "Select commodity asset" vs "Select asset".
 * Pass the exact label string for the target screen.
 */
export async function selectAssetByLabel(
  page: Page,
  label: string,
  assetName: string
): Promise<void> {
  await page.getByLabel(label).click()
  await page.getByRole('option', { name: new RegExp(assetName, 'i') }).click()
  await page.waitForTimeout(200)
}

/** Standard error boundary check — call after every page.goto(). */
export async function assertNoErrorBoundary(page: Page): Promise<void> {
  await expect(page.locator('text=/something went wrong/i')).not.toBeVisible()
}

/** Fetch the most recent backtest run ID. */
export async function getRecentRunId(): Promise<string | null> {
  try {
    const res = await fetch(`${API_ORIGIN}/api/runs`, { signal: AbortSignal.timeout(15_000) })
    const data = await res.json()
    return data.runs?.[0]?.run_id ?? null
  } catch {
    return null
  }
}

/** Fetch the most recent portfolio run ID from the portfolio-specific endpoint. */
export async function getRecentPortfolioRunId(): Promise<string | null> {
  try {
    const res = await fetch(`${API_ORIGIN}/api/portfolio/runs`, {
      signal: AbortSignal.timeout(15_000),
    })
    const data = await res.json()
    return data.runs?.[0]?.run_id ?? null
  } catch {
    return null
  }
}
