import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary } from './helpers'

const STRATEGIES = [
  {
    id: 'ema_crossover',
    asset: 'gold',
    display: 'EMA Crossover',
    params: ['fast_period', 'slow_period'],
    defaults: { fast_period: 50, slow_period: 200 },
  },
  {
    id: 'momentum',
    asset: 'gold',
    display: 'Momentum',
    params: ['lookback_period', 'z_score_window'],
    defaults: { lookback_period: 20, z_score_window: 63, signal_threshold: 0.5 },
  },
  {
    id: 'rsi_reversion',
    asset: 'gold',
    display: 'RSI Reversion',
    params: ['period', 'oversold_threshold', 'overbought_threshold'],
    defaults: { period: 14, oversold_threshold: 30, overbought_threshold: 70 },
  },
  {
    id: 'donchian_breakout',
    asset: 'gold',
    display: 'Donchian Breakout',
    params: ['channel_period'],
    defaults: { channel_period: 20 },
  },
  {
    id: 'carry',
    asset: 'gold',
    display: 'Carry',
    params: ['threshold', 'n_contracts'],
    defaults: { threshold: 0.0, n_contracts: 4 },
  },
  {
    id: 'cot_positioning',
    asset: 'gold',
    display: 'COT Positioning',
    params: ['upper_pct', 'lower_pct'],
    defaults: { upper_pct: 80.0, lower_pct: 20.0 },
  },
  {
    id: 'eia_inventory',
    asset: 'wti',
    display: 'EIA Inventory',
    params: ['threshold'],
    defaults: { threshold: 1.0 },
  },
]

test.describe('Strategy parameter panels', () => {
  for (const s of STRATEGIES) {
    test(`${s.id} on ${s.asset}: parameter inputs render`, async ({ page }) => {
      const encoded = encodeURIComponent(JSON.stringify(s.defaults))
      await page.goto(`/research?asset=${s.asset}&strategy=${s.id}&params=${encoded}`)

      // Vite HMR can throw "Failed to fetch dynamically imported module" mid-suite.
      if (await page.getByText(/something went wrong/i).isVisible().catch(() => false)) {
        await page.reload()
      }

      await expect(page.getByRole('button', { name: s.display }).first()).toBeVisible({
        timeout: 15_000,
      })

      // ParamForm: <label htmlFor={p.name}>{p.name}</label> + NumberInput id={p.name}
      for (const param of s.params) {
        const input = page.locator(`#${param}`)
        await expect(input).toBeVisible({ timeout: 15_000 })
      }

      await assertNoErrorBoundary(page)
    })
  }

  test('wti_brent_spread on wti: parameter inputs render', async ({ page }) => {
    // wti_brent_spread registered in 44a75f1
    const encoded = encodeURIComponent(JSON.stringify({ lookback: 63, threshold: 1.0 }))
    await page.goto(`/research?asset=wti&strategy=wti_brent_spread&params=${encoded}`)

    if (await page.getByText(/something went wrong/i).isVisible().catch(() => false)) {
      await page.reload()
    }

    await expect(page.getByRole('button', { name: /WTI-Brent Spread/i }).first()).toBeVisible({
      timeout: 15_000,
    })
    for (const param of ['lookback', 'threshold']) {
      await expect(page.locator(`#${param}`)).toBeVisible({ timeout: 15_000 })
    }
    await assertNoErrorBoundary(page)
  })
})
