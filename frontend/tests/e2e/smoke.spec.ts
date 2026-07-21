import { test, expect } from '@playwright/test'

/**
 * Platform-wide smoke test — F-Track completion validation.
 * Walks the full research loop verifying each major screen loads correctly.
 * Uses skip guards for screens requiring live data.
 */
test.describe('F-Track Platform Smoke Test', () => {
  test('Full research loop: Market → Intelligence → Portfolio navigates without errors',
    async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', err => errors.push(err.message))
      page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text())
      })

      // 1. Market Overview
      await page.goto('/market')
      await page.waitForLoadState('networkidle')
      await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 10_000 })

      // 2. Asset Detail — click first table row if present
      const firstRow = page.locator('table tbody tr').first()
      if (await firstRow.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await firstRow.click()
        await page.waitForLoadState('networkidle')
        expect(page.url()).toMatch(/\/market\/\w+/)
      }

      // 3. Research Workbench
      await page.goto('/research')
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(/research/)

      // 4. Strategy Builder
      await page.goto(
        '/backtest/new?asset=gold&strategy=ema_crossover&params={"fast_period":50,"slow_period":200}'
      )
      await page.waitForLoadState('networkidle')
      await expect(
        page.getByRole('heading', { name: /strategy builder/i })
      ).toBeVisible({ timeout: 10_000 })

      // 5. Run Explorer
      await page.goto('/runs')
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(/\/runs$/)

      // 6. Intelligence — conditional on curves endpoint being available
      const curveCheck = await page.request.get(
        'http://127.0.0.1:8000/api/curves/available'
      )
      if (curveCheck.ok()) {
        await page.goto('/intelligence')
        await page.waitForLoadState('networkidle')
        await expect(
          page.getByRole('heading', { name: /futures curve/i })
        ).toBeVisible({ timeout: 10_000 })
      }

      // 7. Intelligence Compare
      await page.goto('/intelligence/compare')
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(/intelligence\/compare/)

      // 8. Portfolio Analytics
      await page.goto('/portfolio')
      await page.waitForLoadState('networkidle')
      await expect(
        page.getByRole('button', { name: /launch portfolio backtest/i })
      ).toBeVisible({ timeout: 10_000 })

      // Assert no JS exceptions (filter out non-critical noise)
      const jsErrors = errors.filter(
        e => !e.includes('Warning:') && !e.includes('favicon')
      )
      expect(jsErrors).toHaveLength(0)
    }
  )
})
