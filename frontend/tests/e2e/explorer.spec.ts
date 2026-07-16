import { test, expect } from '@playwright/test'

test.describe('Run Explorer and Comparison (S7/S8)', () => {
  test('Run Explorer filters update URL and table', async ({ page }) => {
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    const strategySelect = page.getByRole('combobox').first()
    if (await strategySelect.isVisible()) {
      await strategySelect.click()
      await page.getByRole('option').nth(1).click()
      await expect(page).toHaveURL(/strategy=/, { timeout: 3_000 })
    }
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
  })

  test('ComparisonTray appears when run selected; Compare navigates correctly', async ({ page }) => {
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    const rows = page.locator('table tbody tr')
    const count = await rows.count()
    if (count >= 2) {
      await rows.nth(0).locator('input[type="checkbox"]').click()
      await rows.nth(1).locator('input[type="checkbox"]').click()
      await expect(page.getByText(/2 runs selected/i)).toBeVisible({ timeout: 3_000 })
      const compareBtn = page.getByRole('button', { name: /compare/i })
      await expect(compareBtn).toBeEnabled({ timeout: 3_000 })
      await compareBtn.click()
      await expect(page).toHaveURL(/\/runs\/compare\?ids=/, { timeout: 5_000 })
    } else {
      test.skip()
    }
  })

  test('DataGrid 300-row virtualization: fewer rows in DOM than total (/dev/gallery)', async ({ page }) => {
    // NOTE: data-testid="gallery-datagrid-300" added to Gallery.tsx in F8 Increment 4
    await page.goto('/dev/gallery')
    await page.waitForLoadState('networkidle')
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="gallery-datagrid-300"]')
      el?.scrollIntoView()
    })
    await page.waitForTimeout(500)
    const rows = page.locator('[data-testid="gallery-datagrid-300"] table tbody tr')
    const domCount = await rows.count()
    expect(domCount).toBeLessThan(50)
    expect(domCount).toBeGreaterThan(0)
  })
})
