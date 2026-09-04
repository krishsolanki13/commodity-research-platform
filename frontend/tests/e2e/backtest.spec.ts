import { test, expect } from '@playwright/test'
import { assertNoErrorBoundary, getRecentRunId } from './helpers'
import type { Page } from '@playwright/test'

async function fillParam(page: Page, param: string, value: string) {
  const input = page.locator(`#${param}`)
  await expect(input).toBeVisible({ timeout: 10_000 })
  await input.fill(value)
  await input.blur()
  await page.waitForTimeout(300)
}

async function evaluateStrategy(page: Page, asset: string, strategy: string, params: Record<string, unknown>) {
  const encoded = encodeURIComponent(JSON.stringify(params))
  await page.goto(`/research?asset=${asset}&strategy=${strategy}&params=${encoded}`)
  const evaluateBtn = page.getByRole('button', { name: /evaluate signal/i })
  await expect(evaluateBtn).toBeEnabled({ timeout: 15_000 })
  await evaluateBtn.click()
  await expect(page.locator('text=/IC/i').first()).toBeVisible({ timeout: 90_000 })
}

test.describe('Strategy Builder and Run Detail (S4/S5)', () => {
  test('Strategy Builder pre-fills from URL and shows Launch button', async ({ page }) => {
    test.setTimeout(60_000)
    const params = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(`/backtest/new?asset=gold&strategy=ema_crossover&params=${params}`)
    await expect(page.getByRole('heading', { name: /strategy builder/i })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByRole('button', { name: /launch backtest/i })).toBeVisible({
      timeout: 5_000,
    })
    // Use spinbutton role — accessible name is "Initial capital" even when label text is "initial_capital (USD)"
    await expect(page.getByRole('spinbutton', { name: /initial capital/i }).first()).toBeVisible({
      timeout: 5_000,
    })
  })

  test('Run Detail tabs switch and ?tab= updates URL', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/runs')
    await page.waitForSelector('table tbody tr', { timeout: 20_000 })
    const rows = page.locator('table tbody tr')
    if ((await rows.count()) === 0) {
      test.skip()
      return
    }
    await rows.first().click()
    await expect(page).toHaveURL(/\/runs\/[^/]+$/, { timeout: 5_000 })
    const overviewTab = page.getByRole('tab', { name: /overview/i })
    await expect(overviewTab).toHaveAttribute('aria-selected', 'true', { timeout: 5_000 })
    await page.getByRole('tab', { name: /signal quality/i }).click()
    await expect(page).toHaveURL(/tab=signal/, { timeout: 3_000 })
  })
})

test.describe('Backtest lifecycle', () => {
  test(
    'EIA Inventory WTI: full path evaluate → configure → launch → Run Detail',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      // eia_inventory registered for backtest in 44a75f1
      test.slow()
      test.setTimeout(360_000)
      const eiaParams = { threshold: 1.0 }
      const evalPromise = page.waitForResponse(
        (r) => r.url().includes('/api/signals/evaluate') && r.ok()
      )
      await evaluateStrategy(page, 'wti', 'eia_inventory', eiaParams)
      const evalRes = await evalPromise
      const body = (await evalRes.json()) as { evaluation?: { ic?: number | null } }
      const evaluation = body.evaluation ?? body

      const configBtn = page.getByRole('button', { name: /Configure backtest/i })
      if (await configBtn.isEnabled()) {
        await configBtn.click()
      } else {
        const qs = new URLSearchParams({
          asset: 'wti',
          strategy: 'eia_inventory',
          params: JSON.stringify(eiaParams),
          evaluation: JSON.stringify(evaluation),
        })
        await page.goto(`/backtest/new?${qs.toString()}`)
      }
      await expect(page).toHaveURL(/\/backtest\/new.*evaluation=/)

      await page.getByRole('button', { name: /Launch/i }).click()
      await expect(page.getByText(/running|queued|launching/i).first()).toBeVisible({
        timeout: 10_000,
      })
      await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 300_000 })
      await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
      const runId = await getRecentRunId()
      expect(runId).toBeTruthy()
      await assertNoErrorBoundary(page)
    }
  )

  test(
    'EMA Crossover Gold: full path evaluate → PATH A → launch → Run Detail',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      // Live ic_band is noise for all strategies (Configure stays disabled by design).
      // PATH A is exercised by threading evaluate JSON into /backtest/new?evaluation=.
      // Under single-worker load (regime/sweep jobs) launch→/runs can exceed 3 minutes.
      test.slow()
      test.setTimeout(360_000)
      const emaParams = { fast_period: 50, slow_period: 200 }
      const evalPromise = page.waitForResponse(
        (r) => r.url().includes('/api/signals/evaluate') && r.ok()
      )
      await evaluateStrategy(page, 'gold', 'ema_crossover', emaParams)
      const evalRes = await evalPromise
      const body = (await evalRes.json()) as { evaluation?: { ic?: number | null } }
      const evaluation = body.evaluation ?? body

      const configBtn = page.getByRole('button', { name: /Configure backtest/i })
      if (await configBtn.isEnabled()) {
        await configBtn.click()
      } else {
        const qs = new URLSearchParams({
          asset: 'gold',
          strategy: 'ema_crossover',
          params: JSON.stringify(emaParams),
          evaluation: JSON.stringify(evaluation),
        })
        await page.goto(`/backtest/new?${qs.toString()}`)
      }
      await expect(page).toHaveURL(/\/backtest\/new.*evaluation=/)

      await page.getByRole('button', { name: /Launch/i }).click()
      await expect(page.getByText(/running|queued|launching/i).first()).toBeVisible({
        timeout: 10_000,
      })
      await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 300_000 })
      await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
      await assertNoErrorBoundary(page)
    }
  )

  test(
    'EMA Crossover Gold: direct launch via override path',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      // Direct launch is as slow as the full IC Gate path under single-worker load.
      test.slow()
      test.setTimeout(360_000)
      const emaParams = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
      await page.goto(
        `/backtest/new?asset=gold&strategy=ema_crossover&evalOverride=1&params=${emaParams}`
      )
      await expect(page.getByText(/IC Gate override|without.*evaluation/i).first()).toBeVisible({
        timeout: 5_000,
      })
      await page.getByRole('button', { name: /Launch/i }).click()
      await expect(page.getByText(/running|queued|launching/i).first()).toBeVisible({
        timeout: 10_000,
      })
      await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 300_000 })
      await assertNoErrorBoundary(page)
    }
  )

  test('Momentum Gold: non-default lookback_period=15 persists in Run Detail', async ({
    page,
  }) => {
    test.setTimeout(180_000)
    const momentumParams = encodeURIComponent(
      JSON.stringify({ lookback_period: 20, z_score_window: 63, signal_threshold: 0.5 })
    )
    await page.goto(
      `/backtest/new?asset=gold&strategy=momentum&evalOverride=1&params=${momentumParams}`
    )
    // Param form loads after GET /api/strategies — wait before fill
    await expect(page.locator('#lookback_period')).toBeVisible({ timeout: 10_000 })
    await fillParam(page, 'lookback_period', '15')
    await page.getByRole('button', { name: /Launch/i }).click()
    await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 120_000 })
    await page.getByRole('tab', { name: /^artifacts$/i }).click()
    await expect(page.locator('pre')).toContainText(/"lookback_period":\s*15/)
    await assertNoErrorBoundary(page)
  })

  test('RSI Reversion Gold: custom oversold=25, overbought=75', async ({ page }) => {
    test.setTimeout(180_000)
    const rsiParams = encodeURIComponent(
      JSON.stringify({ period: 14, oversold_threshold: 30, overbought_threshold: 70 })
    )
    await page.goto(
      `/backtest/new?asset=gold&strategy=rsi_reversion&evalOverride=1&params=${rsiParams}`
    )
    // Param form loads after GET /api/strategies — wait before fill
    await expect(page.locator('#oversold_threshold')).toBeVisible({ timeout: 10_000 })
    await fillParam(page, 'oversold_threshold', '25')
    await fillParam(page, 'overbought_threshold', '75')
    await page.getByRole('button', { name: /Launch/i }).click()
    await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 120_000 })
    await page.getByRole('tab', { name: /^artifacts$/i }).click()
    await expect(page.locator('pre')).toContainText(/"oversold_threshold":\s*25/)
    await expect(page.locator('pre')).toContainText(/"overbought_threshold":\s*75/)
    await assertNoErrorBoundary(page)
  })

  test('Running state visible before auto-navigation to Run Detail', async ({ page }) => {
    test.setTimeout(180_000)
    const emaParams = encodeURIComponent(JSON.stringify({ fast_period: 50, slow_period: 200 }))
    await page.goto(
      `/backtest/new?asset=gold&strategy=ema_crossover&evalOverride=1&params=${emaParams}`
    )
    await page.getByRole('button', { name: /Launch/i }).click()
    await expect(page.getByText(/running|queued|launching|seconds/i).first()).toBeVisible({
      timeout: 10_000,
    })
    await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 120_000 })
    await assertNoErrorBoundary(page)
  })

  test('Donchian Breakout Gold: launches and shows equity curve', async ({ page }) => {
    test.setTimeout(180_000)
    const donchianParams = encodeURIComponent(JSON.stringify({ channel_period: 20 }))
    await page.goto(
      `/backtest/new?asset=gold&strategy=donchian_breakout&evalOverride=1&params=${donchianParams}`
    )
    await page.getByRole('button', { name: /Launch/i }).click()
    await page.waitForURL(/\/runs\/[^/]+$/, { timeout: 120_000 })
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
    await assertNoErrorBoundary(page)
  })
})

let recentRunId: string | null = null

test.describe('Run Detail — all tabs', () => {
  test.beforeAll(async () => {
    recentRunId = await getRecentRunId()
  })

  test('Overview tab: equity curve and Sharpe visible', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await expect(page.locator('canvas').first()).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('text=/Sharpe/i').first()).toBeVisible()
    await assertNoErrorBoundary(page)
  })

  test('Signal Quality tab: renders without error', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await page.getByRole('tab', { name: 'Signal Quality' }).click()
    await page.waitForTimeout(1_000)
    await assertNoErrorBoundary(page)
    await expect(page.locator('[role="tabpanel"][data-state="active"]')).not.toBeEmpty()
  })

  test('Validation tab: Run Validation button visible', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await page.getByRole('tab', { name: 'Validation' }).click()
    await expect(
      page.getByRole('button', { name: /Launch Walk-Forward Validation|Run Validation|Validate/i })
    ).toBeVisible({ timeout: 10_000 })
    await assertNoErrorBoundary(page)
  })

  test('Trades tab: renders without error', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await page.getByRole('tab', { name: 'Trades' }).click()
    await page.waitForTimeout(1_000)
    await assertNoErrorBoundary(page)
    await expect(page.locator('[role="tabpanel"][data-state="active"]')).not.toBeEmpty()
  })

  test('Artifacts tab: renders without error', async ({ page }) => {
    if (!recentRunId) {
      test.skip()
      return
    }
    await page.goto(`/runs/${recentRunId}`)
    await page.getByRole('tab', { name: 'Artifacts' }).click()
    await page.waitForTimeout(1_000)
    await assertNoErrorBoundary(page)
    await expect(page.locator('[role="tabpanel"][data-state="active"]')).not.toBeEmpty()
  })

  test(
    'walk-forward validation launches and shows progress',
    {
      tag: '@slow',
    },
    async ({ page }) => {
      test.slow()
      test.setTimeout(360_000)
      if (!recentRunId) {
        test.skip()
        return
      }
      await page.goto(`/runs/${recentRunId}`)
      await page.getByRole('tab', { name: 'Validation' }).click()
      await page
        .getByRole('button', { name: /Launch Walk-Forward Validation|Run Validation|Validate/i })
        .click()
      await expect(page.getByText(/validating|running|queued/i).first()).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.locator('canvas').or(page.getByText(/out.of.sample|fold/i)).first()).toBeVisible({
        timeout: 300_000,
      })
      await assertNoErrorBoundary(page)
    }
  )
})
