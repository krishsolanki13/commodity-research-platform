import { test, expect } from '@playwright/test'

test.describe('Inc6 — Sweep Explorer & Curve PCA', () => {
  test('/sweeps route loads and shows Sweep Configuration panel', async ({ page }) => {
    await page.goto('/sweeps')
    await page.waitForLoadState('networkidle')

    await expect(
      page.getByRole('heading', { name: /sweep explorer/i }),
    ).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Sweep Configuration')).toBeVisible()
    await expect(page.getByLabel('Select commodity asset')).toBeVisible()
  })

  test('/intelligence/pca route loads and shows PCA Configuration panel', async ({ page }) => {
    await page.goto('/intelligence/pca')
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('heading', { name: /curve pca/i })).toBeVisible({
      timeout: 10_000,
    })
    await expect(page.getByText('PCA Configuration')).toBeVisible()
    await expect(page.getByLabel('Select commodity asset')).toBeVisible()
  })
})
