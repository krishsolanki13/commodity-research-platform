import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary } from './helpers'

test.describe('Inc7 — Data Manager', () => {
  test('Data Manager page loads and QC section is visible for gold', async ({ page }) => {
    test.setTimeout(30_000)

    const qcCheck = await page.request
      .get('http://localhost:8000/api/system/data/qc?asset=gold')
      .catch(() => null)
    if (!qcCheck?.ok()) {
      test.skip()
      return
    }

    await page.goto('/system/data?asset=gold')

    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText('QC Report')).toBeVisible()
    await expect(page.getByText(/Healthy|Warning|Critical/i).first()).toBeVisible({
      timeout: 15_000,
    })
  })
})

test.describe('Data Manager', () => {
  test('page loads with asset selector', async ({ page }) => {
    await page.goto('/system/data')
    await expect(page.getByLabel('Select commodity asset')).toBeVisible({ timeout: 15_000 })
    await assertNoErrorBoundary(page)
  })

  test('Gold COT: records visible, percentile in 0–100 range', async ({ page }) => {
    // COT/EIA are stacked sections after asset selection — not tabs. Use URL asset=.
    await page.goto('/system/data?asset=gold')
    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByText('COT Positioning').scrollIntoViewIfNeeded()
    await expect(page.getByText('COT Net Speculative Positioning')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 10_000 })
    // percentile_rank is chart-only (tooltip). Assert via API: 0–100, not 0–10000.
    const cotRes = await page.request.get('http://localhost:8000/api/system/data/cot?asset=gold')
    if (cotRes.ok()) {
      const body = (await cotRes.json()) as {
        records?: Array<{ percentile_rank?: number | null }>
      }
      const ranks = (body.records ?? [])
        .map((r) => r.percentile_rank)
        .filter((v): v is number => typeof v === 'number')
      for (const rank of ranks) {
        expect(rank).toBeGreaterThanOrEqual(0)
        expect(rank).toBeLessThanOrEqual(100)
      }
    }
    await assertNoErrorBoundary(page)
  })

  test('Brent COT: graceful empty state — no COT data', async ({ page }) => {
    await page.goto('/system/data?asset=brent')
    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByText('COT Positioning').scrollIntoViewIfNeeded()
    await expect(page.getByText(/No COT data available/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/ICE/i).first()).toBeVisible()
    await expect(page.locator('text=/500|internal server/i')).not.toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('WTI EIA: inventory records visible', async ({ page }) => {
    await page.goto('/system/data?asset=wti')
    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByText('EIA Inventory', { exact: true }).scrollIntoViewIfNeeded()
    await expect(page.getByText('EIA Inventory Surprise (z-score)')).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.locator('canvas').first()).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('Gold EIA: graceful "not crude oil" empty state', async ({ page }) => {
    await page.goto('/system/data?asset=gold')
    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByText('EIA Inventory', { exact: true }).scrollIntoViewIfNeeded()
    await expect(page.getByText(/No EIA data available/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/not tracked in EIA inventory|crude oil storage only/i)).toBeVisible()
    await assertNoErrorBoundary(page)
  })
})
