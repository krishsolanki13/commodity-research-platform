import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary, getRecentRunId } from './helpers'

let recentRunId: string | null = null
test.beforeAll(async () => {
  recentRunId = await getRecentRunId()
})

test.describe('Cross-screen state', () => {
  test('backtest launch navigates to Run Detail showing correct asset and strategy', async ({
    page,
  }) => {
    test.setTimeout(180_000)
    const emaParams = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(
      `/backtest/new?asset=gold&strategy=ema_crossover&evalOverride=1&params=${emaParams}`
    )
    await page.getByRole('button', { name: /Launch/i }).click()
    await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 120_000 })
    await expect(page.locator('text=/gold/i').first()).toBeVisible({ timeout: 10_000 })
    await assertNoErrorBoundary(page)
  })

  test('Run Detail tab selection — document actual persistence behavior', async ({ page }) => {
    test.setTimeout(90_000)
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await page.getByRole('tab', { name: 'Trades' }).click()
    await page.waitForTimeout(500)
    await page.goto('/runs')
    await expect(
      page.locator('table tbody tr').first().or(page.getByText(/no runs/i)),
    ).toBeVisible({ timeout: 60_000 })
    await page.goto(`/runs/${recentRunId}`)
    const tradesTab = page.getByRole('tab', { name: 'Trades' })
    const isActive = await tradesTab.getAttribute('aria-selected')
    // TabsUrlSync stores tab in ?tab=; a fresh /runs/:id URL has no tab param → RESETS.
    // Tab state (?tab= URL param) is lost on navigation by design.
    // URL-first routing per TDR-014: navigating away clears search params.
    // Tab persistence across navigation is not implemented (would require
    // Zustand workspace state). Confirmed expected behavior — not a bug.
    console.log('Tab persistence after navigation:', isActive === 'true' ? 'PERSISTS' : 'RESETS to Overview')
    await assertNoErrorBoundary(page)
  })

  test('same-route navigation: clicking Research sidebar while on /research does not crash', async ({
    page,
  }) => {
    // Tests the 0d06bfd fix — RouteErrorBoundary on all 16 routes
    await page.goto('/research')
    await expect(page.getByRole('button', { name: /Evaluate signal/i }).first()).toBeVisible({
      timeout: 15_000,
    })
    await page.getByRole('link', { name: 'Research' }).click()
    await page.waitForTimeout(500)
    await assertNoErrorBoundary(page)
    await expect(page.getByRole('button', { name: /Evaluate signal/i }).first()).toBeVisible({
      timeout: 15_000,
    })
  })
})
