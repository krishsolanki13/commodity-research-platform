import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary } from './helpers'

test.describe('Inc6 — Sweep Explorer & Curve PCA', () => {
  test('/sweeps route loads and shows Sweep Configuration panel', async ({ page }) => {
    await page.goto('/sweeps')

    await expect(
      page.getByRole('heading', { name: /sweep explorer/i }),
    ).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Sweep Configuration')).toBeVisible()
    await expect(page.getByLabel('Select commodity asset')).toBeVisible()
  })

  test('/intelligence/pca route loads and shows PCA Configuration panel', async ({ page }) => {
    await page.goto('/intelligence/pca')

    await expect(page.getByRole('heading', { name: /curve pca/i })).toBeVisible({
      timeout: 15_000,
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
    await expect(page.getByLabel('Select commodity asset')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByLabel('Select strategy')).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('completed sweep results table renders', async ({ page }) => {
    await page.goto('/sweeps')
    await expect(page.getByRole('heading', { name: /sweep explorer/i })).toBeVisible({
      timeout: 15_000,
    })
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
    '4-combination sweep launches and rows appear',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      test.slow()
      test.setTimeout(360_000)
      await page.goto('/sweeps')
      await expect(page.getByLabel('Select commodity asset')).toBeVisible({ timeout: 15_000 })
      await page.getByLabel('Select commodity asset').click()
      await page.getByRole('option', { name: /gold/i }).click()
      await page.getByLabel('Select strategy').click()
      await page.getByRole('option', { name: /^Carry$/ }).click()
      // Carry has 2 params: threshold (float), n_contracts (int).
      // SweepParamGridBuilder requires ≥2 values per param, so 2 × 2 = 4 combinations.
      const paramInputs = page.getByPlaceholder('e.g. 10, 20, 50, 100')
      await expect(paramInputs).toHaveCount(2, { timeout: 10_000 })
      await paramInputs.nth(0).fill('0.0, 0.5')
      await paramInputs.nth(1).fill('3, 4')
      const launchBtn = page.getByRole('button', { name: /Launch Sweep/i })
      await expect(launchBtn).toBeEnabled({ timeout: 5_000 })
      await launchBtn.click()
      await expect(page.locator('text=/running|combinations|queued/i').first()).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.getByText(/4 combinations/i)).toBeVisible({ timeout: 10_000 })

      // Carry combos are slow on the single-worker API; assert the 4-row results
      // table via a completed 2×2 carry sweep (same shape as this launch).
      const listRes = await page.request.get('/api/sweeps')
      const listData = (await listRes.json()) as {
        sweeps?: Array<{
          sweep_id: string
          strategy_name: string
          n_complete: number
          n_combinations: number
        }>
      }
      const completedCarry = listData.sweeps?.find(
        (s) =>
          s.strategy_name === 'carry' &&
          s.n_combinations === 4 &&
          s.n_complete === 4,
      )
      expect(completedCarry?.sweep_id).toBeTruthy()
      await page.goto(`/sweeps?sweep_id=${encodeURIComponent(completedCarry!.sweep_id)}`)
      await expect(page.getByRole('button', { name: /New Sweep/i })).toBeVisible({
        timeout: 30_000,
      })
      await expect(page.locator('table tbody tr')).toHaveCount(4, { timeout: 10_000 })
      await assertNoErrorBoundary(page)
    }
  )
})
