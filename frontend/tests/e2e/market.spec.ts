import { test, expect } from '@playwright/test'

test.describe('Market Overview (S1)', () => {
  test('loads and shows all 6 commodity assets', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/market')
    await page.waitForLoadState('networkidle')
    await page.waitForSelector('table tbody tr', { timeout: 20_000 })
    const rows = page.locator('table tbody tr')
    await expect(rows).toHaveCount(6, { timeout: 20_000 })
    await expect(page.locator('text=/gold/i').first()).toBeVisible()
  })

  test('clicking Gold row navigates to Asset Detail', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/market')
    await page.waitForLoadState('networkidle')
    await page.waitForSelector('table tbody tr', { timeout: 20_000 })
    await page.locator('table tbody tr').filter({ hasText: /gold/i }).first().click()
    await expect(page).toHaveURL(/\/market\/gold/, { timeout: 5_000 })
    await expect(page.locator('text=GC=F').first()).toBeVisible({ timeout: 5_000 })
  })

  test('"Open in Workbench" link on Asset Detail carries context to Research Workbench', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/market/gold')
    await page.waitForLoadState('networkidle')
    const workbenchLink = page.getByRole('link', { name: /open in workbench/i })
    await expect(workbenchLink).toBeVisible({ timeout: 10_000 })
    const href = await workbenchLink.getAttribute('href')
    expect(href).toContain('/research')
    expect(href).toContain('asset=gold')
  })
})
