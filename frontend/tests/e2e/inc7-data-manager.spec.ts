import { test, expect } from '@playwright/test'

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
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 10_000,
    })
    await expect(page.getByText('QC Report')).toBeVisible()
    await expect(page.getByText(/Healthy|Warning|Critical/i).first()).toBeVisible({
      timeout: 15_000,
    })
  })
})
