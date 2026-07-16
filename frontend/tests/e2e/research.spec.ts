import { test, expect } from '@playwright/test'

test.describe('Research Workbench (S3)', () => {
  test('loads with asset pre-selected from URL param', async ({ page }) => {
    test.setTimeout(60_000)
    const params = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(`/research?asset=gold&strategy=ema_crossover&params=${params}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByText('EMA Crossover').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/ema_50/i).first()).toBeVisible({ timeout: 5_000 })
  })

  test('evaluate chain runs and IC Gate shows result', async ({ page }) => {
    test.setTimeout(90_000)
    const params = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(`/research?asset=gold&strategy=ema_crossover&params=${params}`)
    await page.waitForLoadState('networkidle')

    const evaluateBtn = page.getByRole('button', { name: /evaluate signal/i })
    await expect(evaluateBtn).toBeEnabled({ timeout: 10_000 })
    await evaluateBtn.click()

    // Real Gold EMA 50/200 evaluation — IC ≈ 0.006–0.012, band: noise
    await expect(page.getByText(/ic\s*:/i).first()).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText(/noise/i).first()).toBeVisible({ timeout: 5_000 })
    const configureBtn = page.getByRole('button', { name: /configure backtest/i })
    await expect(configureBtn).toBeDisabled({ timeout: 5_000 })
  })
})
