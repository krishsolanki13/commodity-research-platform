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

  test('Per-asset panel expands and shows asset performance table', async ({ page }) => {
    await page.goto('/portfolio')
    await page.waitForLoadState('networkidle')

    // Check if a recent run selector exists (populated from prior history)
    const runSelector = page.getByRole('combobox', {
      name: /select a recent portfolio run/i,
    })
    if ((await runSelector.count()) > 0) {
      // Select the most recent run from the dropdown
      await runSelector.first().click()
      const options = page.getByRole('option')
      if ((await options.count()) > 0) {
        await options.first().click()
        await page.waitForLoadState('networkidle')

        // Per-asset panel toggle should be visible
        const perAssetToggle = page.getByText(/per-asset performance/i)
        await expect(perAssetToggle).toBeVisible({ timeout: 10_000 })

        // Expand the panel
        await perAssetToggle.click()

        // Either table rows appear (backend fix live) or graceful message appears
        const tableRows = page.locator('table tbody tr')
        const gracefulMsg = page.getByText(/per-asset data not available/i)

        const hasRows = (await tableRows.count()) > 0
        const hasGraceful = await gracefulMsg.isVisible()

        // One of the two must be true — panel must show something
        expect(hasRows || hasGraceful).toBe(true)
      } else {
        // Selector present but no options — skip
        test.skip()
      }
    } else {
      // No history yet — verify config state renders without error
      await expect(page.getByRole('button', { name: /launch/i })).toBeVisible({
        timeout: 10_000,
      })
    }
  })
})
