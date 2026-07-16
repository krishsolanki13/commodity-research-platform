import { http, HttpResponse } from 'msw'
import { MOCK_RUN_ID } from '../fixtures/run-detail'

export const backtestHandlers = [
  http.post('http://localhost:8000/api/backtests', () =>
    HttpResponse.json({ run_id: MOCK_RUN_ID, status: 'queued' }, { status: 202 })
  ),
  // Known MOCK_RUN_ID → complete immediately
  http.get(
    `http://localhost:8000/api/backtests/${MOCK_RUN_ID}/status`,
    () =>
      HttpResponse.json({
        run_id: MOCK_RUN_ID,
        status: 'complete',
        error: null,
        executed_at: '2026-07-15T12:00:03Z',
      })
  ),
  // Wildcard fallback → queued (for arbitrary runIds in polling tests)
  http.get(
    'http://localhost:8000/api/backtests/:runId/status',
    ({ params }) =>
      HttpResponse.json({
        run_id: params.runId as string,
        status: 'queued',
        error: null,
        executed_at: null,
      })
  ),
]
