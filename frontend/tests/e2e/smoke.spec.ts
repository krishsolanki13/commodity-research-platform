import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary, getRecentRunId } from './helpers'

/**
 * Platform-wide smoke test — F-Track completion validation.
 * Walks the full research loop verifying each major screen loads correctly.
 * Uses skip guards for screens requiring live data.
 */
test.describe('F-Track Platform Smoke Test', () => {
  test('Full research loop: Market → Intelligence → Portfolio navigates without errors', async ({
    page,
  }) => {
    test.setTimeout(120_000)
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })

    // 1. Market Overview
    await page.goto('/market')
    await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 15_000 })

    // 2. Asset Detail — click first table row if present
    const firstRow = page.locator('table tbody tr').first()
    if (await firstRow.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await firstRow.click()
      await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
      expect(page.url()).toMatch(/\/market\/\w+/)
    }

    // 3. Research Workbench
    await page.goto('/research')
    await expect(page.getByRole('button', { name: /Evaluate/i }).first()).toBeVisible({
      timeout: 15_000,
    })
    await expect(page).toHaveURL(/research/)

    // 4. Strategy Builder
    await page.goto(
      '/backtest/new?asset=gold&strategy=ema_crossover&params={"fast_period":50,"slow_period":200}'
    )
    await expect(page.getByRole('heading', { name: /strategy builder/i })).toBeVisible({
      timeout: 15_000,
    })

    // 5. Run Explorer
    await page.goto('/runs')
    await expect(
      page.locator('table tbody tr').first().or(page.getByText(/no runs yet/i)),
    ).toBeVisible({ timeout: 15_000 })
    await expect(page).toHaveURL(/\/runs$/)

    // 6. Intelligence — conditional on curves endpoint being available
    const curveCheck = await page.request.get('http://127.0.0.1:8000/api/curves/available')
    if (curveCheck.ok()) {
      await page.goto('/intelligence')
      await expect(page.getByRole('heading', { name: /futures curve/i })).toBeVisible({
        timeout: 15_000,
      })
    }

    // 7. Intelligence Compare
    await page.goto('/intelligence/compare')
    await expect(page.getByRole('heading', { name: /curve comparison/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page).toHaveURL(/intelligence\/compare/)

    // 8. Portfolio Analytics
    await page.goto('/portfolio')
    await expect(page.getByRole('button', { name: /launch portfolio backtest/i })).toBeVisible({
      timeout: 15_000,
    })

    // Assert no JS exceptions (filter out non-critical noise)
    const jsErrors = errors.filter((e) => !e.includes('Warning:') && !e.includes('favicon'))
    expect(jsErrors).toHaveLength(0)
  })
})

let recentRunId: string | null = null

test.describe('Navigation — all routes load without error boundary', () => {
  test.describe.configure({ timeout: 90_000 })

  test.beforeAll(async () => {
    recentRunId = await getRecentRunId()
  })

  test('/ and /market show commodity table', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/market/)
    await expect(page.locator('table tbody tr').filter({ hasText: /gold/i }).first()).toBeVisible({
      timeout: 20_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/market/gold shows price chart canvas', async ({ page }) => {
    await page.goto('/market/gold')
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/market/silver shows price chart canvas', async ({ page }) => {
    await page.goto('/market/silver')
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/market/wti shows price chart canvas', async ({ page }) => {
    await page.goto('/market/wti')
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/research shows strategy picker buttons', async ({ page }) => {
    await page.goto('/research')
    await expect(page.getByRole('button', { name: /EMA Crossover/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/backtest/new shows launch button', async ({ page }) => {
    await page.goto('/backtest/new')
    await expect(page.getByRole('button', { name: /launch backtest/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/runs shows run list or empty state', async ({ page }) => {
    // @bug 822 runs causes ~30s load — known, not fixed in this module
    await page.goto('/runs')
    const rows = page.locator('table tbody tr')
    const empty = page.getByText(/no runs yet/i)
    await expect(rows.first().or(empty)).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/runs/:id shows equity curve canvas', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/runs/compare shows compare UI', async ({ page }) => {
    await page.goto('/runs/compare')
    await expect(page.getByRole('heading', { name: /run comparison/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/intelligence shows futures curve screen', async ({ page }) => {
    await page.goto('/intelligence?asset=gold')
    await expect(page.getByRole('button', { name: /View Curve/i })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByRole('button', { name: /View Curve/i }).click()
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 20_000 })
    await assertNoErrorBoundary(page)
  })

  test('/intelligence/pca shows PCA configuration', async ({ page }) => {
    await page.goto('/intelligence/pca')
    await expect(page.getByRole('heading', { name: /curve pca/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText('PCA Configuration')).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('/intelligence/compare shows compare UI', async ({ page }) => {
    await page.goto('/intelligence/compare')
    await expect(page.getByRole('heading', { name: /curve comparison/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/sweeps shows sweep configuration UI', async ({ page }) => {
    await page.goto('/sweeps')
    await expect(page.getByRole('heading', { name: /sweep explorer/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText('Sweep Configuration')).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('/portfolio shows portfolio configuration UI', async ({ page }) => {
    await page.goto('/portfolio')
    await expect(page.getByRole('button', { name: /launch portfolio backtest/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })

  test('/system/data shows data manager content', async ({ page }) => {
    await page.goto('/system/data')
    await expect(page.getByRole('heading', { name: /data manager/i })).toBeVisible({
      timeout: 15_000,
    })
    await assertNoErrorBoundary(page)
  })
})
