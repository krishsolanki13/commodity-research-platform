import { test, expect } from '@playwright/test'

test.describe('F16 Inc6 polish', () => {
  test('Run Explorer shows populated run rows', async ({ page }) => {
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 10_000 })
    const firstRow = page.locator('table tbody tr').first()
    await expect(firstRow).toBeVisible()
    const text = await firstRow.textContent()
    expect(text?.trim().length).toBeGreaterThan(0)
  })

  test('/runs/compare renders without redirect', async ({ page }) => {
    await page.goto('/runs/compare')
    await expect(page).not.toHaveURL(/\/runs\/?$/)
    await expect(page.locator('h1, h2, h3, [data-testid="comparison"]').first()).toBeVisible({
      timeout: 5_000,
    })
  })

  test('Asset selector dropdown has dark background', async ({ page }) => {
    await page.goto('/research')
    const trigger = page.locator('[role="combobox"]').first()
    await trigger.click()
    const panel = page.locator('[data-radix-popper-content-wrapper]').first()
    await expect(panel).toBeVisible({ timeout: 3_000 })
    const bg = await panel.locator(':scope > *').first().evaluate((el) => {
      return getComputedStyle(el).backgroundColor
    })
    // Must not be white (rgb(255, 255, 255))
    expect(bg).not.toBe('rgb(255, 255, 255)')
  })

  test('Trade direction filter fires server-side request', async ({ page }) => {
    const res = await page.request.get('/api/runs')
    const data = (await res.json()) as { runs?: Array<{ run_id: string }> }
    const runId = data.runs?.[0]?.run_id
    if (!runId) {
      test.skip()
      return
    }

    await page.goto(`/runs/${runId}`)
    await page.getByRole('tab', { name: /trades/i }).click()

    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/trades') && req.url().includes('direction=long')
    )
    await page.getByRole('button', { name: /^long$/i }).click()
    const request = await requestPromise
    expect(request.url()).toContain('direction=long')
    expect(request.url()).not.toContain('page_size=500')
  })
})
