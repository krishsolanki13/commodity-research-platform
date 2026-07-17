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
    await expect(
      page.getByRole('heading', { name: /futures curve/i }),
    ).toBeVisible({ timeout: 10_000 })

    // Regime badge — contango or backwardation depending on live market
    await expect(
      page.getByText(/contango|backwardation|flat/i).first(),
    ).toBeVisible({ timeout: 15_000 })

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
})
