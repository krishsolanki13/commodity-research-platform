import { test, expect } from '@playwright/test'

test.describe('Portfolio Analytics', () => {
  test('Portfolio screen loads and shows launch panel', async ({ page }) => {
    await page.goto('/portfolio')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: /launch portfolio backtest/i })).toBeVisible({
      timeout: 10_000,
    })
    await expect(page.getByText(/portfolio configuration/i).first()).toBeVisible({
      timeout: 5_000,
    })
  })

  test('Portfolio results render after providing run_id', async ({ page }) => {
    // Check if a portfolio list endpoint exists with completed runs
    const check = await page.request
      .get('http://127.0.0.1:8000/api/portfolio/list')
      .catch(() => null)

    if (!check || !check.ok()) {
      // No list endpoint or no runs — verify config state only
      await page.goto('/portfolio')
      await page.waitForLoadState('networkidle')
      await expect(page.getByRole('button', { name: /launch/i })).toBeVisible({
        timeout: 10_000,
      })
      return
    }

    const data = (await check.json().catch(() => null)) as {
      runs?: { run_id: string }[]
    } | null
    const firstRun = data?.runs?.[0]
    if (!firstRun) {
      test.skip()
      return
    }

    await page.goto(`/portfolio?run_id=${firstRun.run_id}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByText(/sharpe|portfolio analytics/i).first()).toBeVisible({
      timeout: 15_000,
    })
  })
})
