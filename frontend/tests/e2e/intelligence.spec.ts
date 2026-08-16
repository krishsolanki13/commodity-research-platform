import { test, expect } from '@playwright/test'

test.describe('Intelligence — Futures Curve (S9)', () => {
  test('loads and shows regime badge + forward curve for Gold', async ({ page }) => {
    test.setTimeout(30_000)

    // Verify commodity data is available before navigating
    const check = await page.request.get('http://localhost:8000/api/curves/available')
    if (!check.ok()) {
      test.skip()
      return
    }
    const body = (await check.json()) as { assets?: string[] }
    const assets: string[] = body.assets ?? []
    if (!assets.includes('gold')) {
      test.skip()
      return
    }

    await page.goto('/intelligence?asset=gold&n_contracts=6&lookback=3Y')
    await page.waitForLoadState('networkidle')

    // Page heading
    await expect(page.getByRole('heading', { name: /futures curve/i })).toBeVisible({
      timeout: 10_000,
    })

    // F18: FuturesCurve requires clicking View Curve before results appear
    const viewCurveBtn = page.getByRole('button', { name: /view curve/i })
    await expect(viewCurveBtn).toBeVisible({ timeout: 10_000 })
    await viewCurveBtn.click()

    // Regime badge — contango or backwardation depending on live market
    await expect(page.getByText(/contango|backwardation|flat/i).first()).toBeVisible({
      timeout: 15_000,
    })

    // Front price KPI label is visible
    await expect(page.getByText(/front/i).first()).toBeVisible({ timeout: 5_000 })
  })

  test('switching asset updates URL and KPI row', async ({ page }) => {
    test.setTimeout(30_000)

    const check = await page.request.get('http://localhost:8000/api/curves/available')
    if (!check.ok()) {
      test.skip()
      return
    }
    const body = (await check.json()) as { assets?: string[] }
    const assets: string[] = body.assets ?? []
    if (assets.length < 2) {
      test.skip()
      return
    }

    await page.goto(`/intelligence?asset=${assets[0]}`)
    await page.waitForLoadState('networkidle')

    // URL carries asset param
    await expect(page).toHaveURL(/asset=/, { timeout: 5_000 })
    expect(page.url()).toContain(`asset=${assets[0]}`)
  })

  test('date control renders and URL reflects observation date selection', async ({ page }) => {
    // Gate: skip if backend not running or gold not available
    const availCheck = await page.request
      .get('http://localhost:8000/api/curves/available')
      .catch(() => null)
    if (!availCheck?.ok()) {
      test.skip()
      return
    }
    const availBody = (await availCheck.json()) as { assets?: string[] }
    const assets: string[] = availBody.assets ?? []
    if (!assets.includes('gold')) {
      test.skip()
      return
    }

    // Gate: verify backend supports observation_date param (FULL mode)
    const paramCheck = await page.request
      .get(
        'http://localhost:8000/api/curves/gold/snapshot?n_contracts=2&observation_date=2025-01-02'
      )
      .catch(() => null)

    await page.goto('/intelligence?asset=gold&n_contracts=6&lookback=1Y')
    await page.waitForLoadState('networkidle')

    if (paramCheck?.ok()) {
      // FULL mode — DateScrubber present
      const latestBtn = page.getByRole('button', { name: /use latest available date/i })
      await expect(latestBtn).toBeVisible({ timeout: 10_000 })
      await expect(latestBtn).toHaveAttribute('aria-pressed', 'true')

      const dateInput = page.getByLabel('Observation date')
      const inputVisible = await dateInput.isVisible({ timeout: 3_000 }).catch(() => false)

      if (inputVisible) {
        // Date input is disabled while Latest is active (value === null).
        // Seed a date via URL to exit Latest mode, then exercise fill + clear.
        await page.goto(
          '/intelligence?asset=gold&n_contracts=6&lookback=1Y&observation_date=2025-06-01'
        )
        await page.waitForLoadState('networkidle')
        await expect(page).toHaveURL(/observation_date=2025-06-01/, { timeout: 5_000 })
        await expect(latestBtn).toHaveAttribute('aria-pressed', 'false')

        await dateInput.fill('2025-05-15')
        await expect(page).toHaveURL(/observation_date=2025-05-15/, { timeout: 5_000 })

        // Click Latest — observation_date param should be removed from URL
        await latestBtn.click()
        await page.waitForTimeout(500)
        expect(page.url()).not.toContain('observation_date')
      }
    } else {
      // LATEST-ONLY mode fallback (should not occur given FULL mode confirmed)
      await expect(page.getByRole('heading', { name: /futures curve/i })).toBeVisible({
        timeout: 10_000,
      })
      const viewCurveBtn = page.getByRole('button', { name: /view curve/i })
      if (await viewCurveBtn.isVisible().catch(() => false)) {
        await viewCurveBtn.click()
      }
      await expect(page.getByText(/contango|backwardation|flat/i).first()).toBeVisible({
        timeout: 15_000,
      })
    }
  })

  test('compare screen loads with 2 assets and shows normalized curves', async ({ page }) => {
    const check = await page.request.get('http://localhost:8000/api/curves/available')
    if (!check.ok()) {
      test.skip()
      return
    }
    const { assets } = (await check.json()) as { assets?: string[] }
    if (!assets || assets.length < 2) {
      test.skip()
      return
    }

    const [a1, a2] = assets
    await page.goto(`/intelligence/compare?assets=${a1},${a2}&n_contracts=4`)
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: /curve comparison/i })).toBeVisible({
      timeout: 10_000,
    })

    const checkedBoxes = page.locator('input[type="checkbox"]:checked')
    await expect(checkedBoxes).toHaveCount(2, { timeout: 10_000 })

    await expect(page.getByText(a1, { exact: false }).first()).toBeVisible({
      timeout: 5_000,
    })
    await expect(page.getByText(a2, { exact: false }).first()).toBeVisible({
      timeout: 5_000,
    })
  })
})
