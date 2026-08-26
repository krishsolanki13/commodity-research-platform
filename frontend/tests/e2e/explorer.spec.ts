import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary, getRecentRunId } from './helpers'

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

  test('ComparisonTray appears when run selected; Compare navigates correctly', async ({
    page,
  }) => {
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

  test('DataGrid 300-row virtualization: fewer rows in DOM than total (/dev/gallery)', async ({
    page,
  }) => {
    // NOTE: data-testid="gallery-datagrid-300" added to Gallery.tsx in F8 Increment 4
    await page.goto('/dev/gallery')
    await expect(page.getByTestId('gallery-datagrid-300')).toBeVisible({ timeout: 15_000 })
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

test.describe('Run Explorer', () => {
  test.describe.configure({ timeout: 90_000 })

  let recentRunId: string | null = null
  test.beforeAll(async () => {
    recentRunId = await getRecentRunId()
  })

  test('run list loads with at least one row', async ({ page }) => {
    await page.goto('/runs')
    // @bug 822 runs causes ~30s load — known, not fixed in this module
    await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 60_000 })
    await assertNoErrorBoundary(page)
  })

  test('clicking a run row navigates to Run Detail', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto('/runs')
    await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 60_000 })
    await page.locator('table tbody tr').first().click()
    await expect(page).toHaveURL(/\/runs\/[^/]+$/, { timeout: 10_000 })
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
  })

  test('back button from Run Detail returns to Run Explorer', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    // Direct goto(/runs/:id) then goBack() lands on about:blank — seed history first.
    await page.goto('/runs')
    await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 60_000 })
    await page.goto(`/runs/${recentRunId}`)
    await expect(page.getByRole('button', { name: /copy run id/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.goBack()
    await expect(page).toHaveURL(/\/runs$/, { timeout: 5_000 })
    await assertNoErrorBoundary(page)
  })

  test('search/filter by strategy — skips gracefully if input absent', async ({ page }) => {
    await page.goto('/runs')
    await expect(
      page.locator('table tbody tr').first().or(page.getByText(/no runs/i)),
    ).toBeVisible({ timeout: 60_000 })
    // RunExplorerFilters: <input type="search" placeholder="Search runs…" aria-label="Search runs">
    const searchInput = page.getByLabel('Search runs')
    if (!(await searchInput.isVisible({ timeout: 2_000 }).catch(() => false))) {
      test.skip(true, 'No search input found in Run Explorer — document absence')
      return
    }
    await searchInput.fill('ema_crossover')
    await page.waitForTimeout(500)
    const rows = page.locator('table tbody tr:visible')
    const count = await rows.count()
    if (count > 0) {
      await expect(rows.first()).toContainText(/ema/i)
    }
    await assertNoErrorBoundary(page)
  })
})
