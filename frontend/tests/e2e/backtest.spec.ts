import { test, expect } from '@playwright/test'

test.describe('Strategy Builder and Run Detail (S4/S5)', () => {
  test('Strategy Builder pre-fills from URL and shows Launch button', async ({ page }) => {
    test.setTimeout(60_000)
    const params = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(`/backtest/new?asset=gold&strategy=ema_crossover&params=${params}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('heading', { name: /strategy builder/i })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('button', { name: /launch backtest/i })).toBeVisible({ timeout: 5_000 })
    // Use spinbutton role — accessible name is "Initial capital" even when label text is "initial_capital (USD)"
    await expect(page.getByRole('spinbutton', { name: /initial capital/i }).first()).toBeVisible({ timeout: 5_000 })
  })

  test('Run Detail tabs switch and ?tab= updates URL', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/runs')
    await page.waitForLoadState('networkidle')
    await page.waitForSelector('table tbody tr', { timeout: 20_000 })
    const rows = page.locator('table tbody tr')
    if (await rows.count() === 0) {
      test.skip()
      return
    }
    await rows.first().click()
    await expect(page).toHaveURL(/\/runs\/[^/]+$/, { timeout: 5_000 })
    const overviewTab = page.getByRole('tab', { name: /overview/i })
    await expect(overviewTab).toHaveAttribute('aria-selected', 'true', { timeout: 5_000 })
    await page.getByRole('tab', { name: /signal quality/i }).click()
    await expect(page).toHaveURL(/tab=signal/, { timeout: 3_000 })
  })
})
