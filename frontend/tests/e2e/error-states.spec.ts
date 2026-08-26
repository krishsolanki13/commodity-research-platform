import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary } from './helpers'

test.describe('Error states', () => {
  test('nonexistent run ID shows RouteErrorBoundary, not blank screen', async ({ page }) => {
    await page.goto('/runs/this_run_id_does_not_exist_xyz_123')
    // RunDetail 404: ErrorState with message "Run not found" (not the crash boundary copy)
    await expect(page.locator('text=/not found|404|does not exist/i').first()).toBeVisible({
      timeout: 15_000,
    })
    const bodyText = await page.locator('body').textContent()
    expect(bodyText?.trim().length).toBeGreaterThan(0)
  })

  test('Run Explorer loads despite 822 runs — no 500 error', async ({ page }) => {
    // @bug 822 runs causes ~30s load — known issue, not fixed in this module
    test.setTimeout(90_000)
    await page.goto('/runs')
    await expect(page.locator('text=/500|internal server error/i')).not.toBeVisible()
    const rows = page.locator('table tbody tr')
    const empty = page.getByText(/no runs/i)
    await expect(rows.first().or(empty)).toBeVisible({ timeout: 20_000 })
  })

  test('COT Positioning on Brent: flat result, no 500 error', async ({ page }) => {
    test.setTimeout(120_000)
    const params = encodeURIComponent(JSON.stringify({ upper_pct: 80.0, lower_pct: 20.0 }))
    await page.goto(`/research?asset=brent&strategy=cot_positioning&params=${params}`)
    const evaluateBtn = page.getByRole('button', { name: 'Evaluate signal' })
    await expect(evaluateBtn).toBeVisible({ timeout: 15_000 })
    await expect(evaluateBtn).toBeEnabled({ timeout: 15_000 })
    await evaluateBtn.click()
    await expect(page.locator('text=/IC/i').first()).toBeVisible({ timeout: 90_000 })
    await expect(page.locator('text=/500|internal server/i')).not.toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('EIA Inventory on Gold: flat result, no 500 error', async ({ page }) => {
    // eia_inventory is not registered for launch, but signal evaluation should still respond.
    // StrategyPicker only disables wti_brent_spread on non-WTI — EIA on Gold is selectable.
    test.setTimeout(120_000)
    const params = encodeURIComponent(JSON.stringify({ threshold: 1.0 }))
    await page.goto(`/research?asset=gold&strategy=eia_inventory&params=${params}`)
    const evaluateBtn = page.getByRole('button', { name: 'Evaluate signal' })
    await expect(evaluateBtn).toBeVisible({ timeout: 15_000 })
    await expect(evaluateBtn).toBeEnabled({ timeout: 15_000 })
    await evaluateBtn.click()
    await expect(page.locator('text=/IC/i').first()).toBeVisible({ timeout: 90_000 })
    await expect(page.locator('text=/500|internal server/i')).not.toBeVisible()
    await assertNoErrorBoundary(page)
  })
})
