import { http, HttpResponse } from 'msw'
import { goldEmaRunDetailFixture, MOCK_RUN_ID } from '../fixtures/run-detail'
import { goldTradesFixture } from '../fixtures/run-trades'
import { goldOhlcvFixture } from '../fixtures/gold-ohlcv'

// Build series from the shared OHLCV fixture so indices are consistent
const equityValues = goldOhlcvFixture.data.index.map((_: number, i: number) => 1_000_000 + i * 500)
const pnlValues = goldOhlcvFixture.data.index.map((_: number, i: number) =>
  i % 3 === 0 ? 500 : -200
)

const equitySeriesFixture = {
  run_id: MOCK_RUN_ID,
  name: 'equity_curve',
  data: {
    index: goldOhlcvFixture.data.index,
    columns: { value: equityValues },
  },
}

const pnlSeriesFixture = {
  run_id: MOCK_RUN_ID,
  name: 'pnl',
  data: {
    index: goldOhlcvFixture.data.index,
    columns: { value: pnlValues },
  },
}

export const runsDetailHandlers = [
  // ── Specific MOCK_RUN_ID handlers BEFORE the wildcard ──────────────────────
  // MSW matches in registration order; wildcard would intercept if listed first.

  http.get(`http://localhost:8000/api/runs/${MOCK_RUN_ID}`, () =>
    HttpResponse.json(goldEmaRunDetailFixture)
  ),

  http.get(`http://localhost:8000/api/runs/${MOCK_RUN_ID}/series/equity_curve`, () =>
    HttpResponse.json(equitySeriesFixture)
  ),

  http.get(`http://localhost:8000/api/runs/${MOCK_RUN_ID}/series/pnl`, () =>
    HttpResponse.json(pnlSeriesFixture)
  ),

  http.get(`http://localhost:8000/api/runs/${MOCK_RUN_ID}/trades`, () =>
    HttpResponse.json(goldTradesFixture)
  ),

  // ── Wildcard fallback → 404 for unknown run IDs ─────────────────────────────
  http.get('http://localhost:8000/api/runs/:runId', ({ params }) =>
    HttpResponse.json(
      {
        error: {
          code: 'RUN_NOT_FOUND',
          message: `Run '${String(params.runId)}' not found.`,
        },
      },
      { status: 404 }
    )
  ),
]
