import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function auditPage(page: Page) {
  const builder = new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.animate-shimmer')
  const results = await builder.analyze()
  const criticalOrSerious = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious'
  )
  if (criticalOrSerious.length > 0) {
    console.log('A11y violations:', JSON.stringify(criticalOrSerious, null, 2))
  }
  expect(criticalOrSerious).toHaveLength(0)
}

test.describe('Accessibility Audit (Axe)', () => {
  test('Market Overview has no critical/serious a11y violations', async ({ page }) => {
    await page.goto('/market')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    await auditPage(page)
  })

  test('Research Workbench has no critical/serious a11y violations', async ({ page }) => {
    await page.goto('/research')
    await page.waitForLoadState('networkidle')
    await auditPage(page)
  })

  test('Strategy Builder has no critical/serious a11y violations', async ({ page }) => {
    await page.goto('/backtest/new?asset=gold&strategy=ema_crossover&params={"fast_period":50,"slow_period":200}')
    await page.waitForLoadState('networkidle')
    await auditPage(page)
  })

  test('Run Detail has no critical/serious a11y violations', async ({ page }) => {
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    const rows = page.locator('table tbody tr')
    if (await rows.count() > 0) {
      await rows.first().click()
      await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 5_000 })
      await page.waitForLoadState('networkidle')
      await auditPage(page)
    } else {
      test.skip()
    }
  })

  test('Run Explorer has no critical/serious a11y violations', async ({ page }) => {
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    await auditPage(page)
  })
})
