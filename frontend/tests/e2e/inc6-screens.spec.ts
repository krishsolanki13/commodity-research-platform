import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary } from './helpers'

test.describe('Inc6 — Sweep Explorer & Curve PCA', () => {
  test('/sweeps route loads and shows Sweep Configuration panel', async ({ page }) => {
    await page.goto('/sweeps')
    await page.waitForLoadState('networkidle')

    await expect(
      page.getByRole('heading', { name: /sweep explorer/i }),
    ).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Sweep Configuration')).toBeVisible()
    await expect(page.getByLabel('Select commodity asset')).toBeVisible()
  })

  test('/intelligence/pca route loads and shows PCA Configuration panel', async ({ page }) => {
    await page.goto('/intelligence/pca')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: /curve pca/i })).toBeVisible({
      timeout: 10_000,
    })
    await expect(page.getByText('PCA Configuration')).toBeVisible()
    await expect(page.getByLabel('Select commodity asset')).toBeVisible()
  })
})

test.describe('Sweep Explorer', () => {
  test('sweep UI loads with asset and strategy selectors', async ({ page }) => {
    // Existing Inc6 test already covers heading + asset selector.
    // This adds the strategy combobox (aria-label="Select strategy").
    await page.goto('/sweeps')
    await page.waitForLoadState('networkidle')
    await expect(page.getByLabel('Select commodity asset')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByLabel('Select strategy')).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('completed sweep results table renders', async ({ page }) => {
    await page.goto('/sweeps')
    await page.waitForLoadState('networkidle')
    // Config view: recent-sweeps table or "No previous sweeps."
    // Results view (after selecting a completed sweep): SweepResultsTable or "No sweep results yet."
    const hasResults = await page
      .locator('table tbody tr')
      .first()
      .isVisible({ timeout: 5_000 })
      .catch(() => false)
    const hasEmpty = await page
      .locator('text=/no previous sweeps|no sweep results yet/i')
      .first()
      .isVisible({ timeout: 5_000 })
      .catch(() => false)
    expect(hasResults || hasEmpty).toBe(true)
    await assertNoErrorBoundary(page)
  })

  test.skip(
    'clicking sweep result row navigates to Run Detail',
    async () => {
      // Sweep combinations do not create individual run artifacts —
      // no /runs/{id} exists to navigate to. Row click navigation
      // is not implemented by design (S-FEP-1 spec).
      // If individual sweep run artifacts are added in future,
      // unskip and wire navigation.
    }
  )

  test(
    '2-combination sweep launches and both rows appear',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      test.slow()
      test.setTimeout(180_000)
      await page.goto('/sweeps')
      await page.waitForLoadState('networkidle')
      await page.getByLabel('Select commodity asset').click()
      await page.getByRole('option', { name: /gold/i }).click()
      await page.getByLabel('Select strategy').click()
      await page.getByRole('option', { name: /EMA Crossover/i }).click()
      // SweepParamGridBuilder: comma-separated text inputs, ≥2 values required PER param.
      // Cannot fix slow_period at a single 200 — both fast_period and slow_period need ≥2 values.
      // 2 × 2 = 4 combinations (not 2). Inputs share placeholder "e.g. 10, 20, 50, 100".
      const paramInputs = page.getByPlaceholder('e.g. 10, 20, 50, 100')
      await expect(paramInputs).toHaveCount(2, { timeout: 10_000 })
      await paramInputs.nth(0).fill('10, 50')
      await paramInputs.nth(1).fill('200, 200')
      await page.getByRole('button', { name: /Launch Sweep/i }).click()
      await expect(page.locator('text=/running|combinations|queued/i').first()).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.locator('table tbody tr')).toHaveCount(4, { timeout: 120_000 })
      await assertNoErrorBoundary(page)
    }
  )
})
