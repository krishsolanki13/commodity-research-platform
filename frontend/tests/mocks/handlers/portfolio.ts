import { http, HttpResponse } from 'msw'
import {
  portfolioSummaryFixture,
  portfolioStatusCompleteFixture,
  portfolioEquityFixture,
  portfolioRiskFixture,
  portfolioCorrelationFixture,
  portfolioAssetsFixture,
  MOCK_PORTFOLIO_RUN_ID,
} from '../fixtures/portfolio'

export const portfolioHandlers = [
  http.post('http://localhost:8000/api/portfolio/run', () =>
    HttpResponse.json(
      { run_id: MOCK_PORTFOLIO_RUN_ID, status: 'queued' },
      { status: 202 }
    )
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/status`,
    () => HttpResponse.json(portfolioStatusCompleteFixture)
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/summary`,
    () => HttpResponse.json(portfolioSummaryFixture)
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/equity`,
    () => HttpResponse.json(portfolioEquityFixture)
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/risk`,
    () => HttpResponse.json(portfolioRiskFixture)
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/correlation`,
    () => HttpResponse.json(portfolioCorrelationFixture)
  ),
  http.get(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}/assets`,
    () => HttpResponse.json(portfolioAssetsFixture)
  ),
  http.delete(
    `http://localhost:8000/api/portfolio/${MOCK_PORTFOLIO_RUN_ID}`,
    () =>
      HttpResponse.json({ deleted: true, run_id: MOCK_PORTFOLIO_RUN_ID })
  ),
  http.get(
    'http://localhost:8000/api/portfolio/:runId/status',
    () =>
      HttpResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Portfolio run not found' } },
        { status: 404 }
      )
  ),
]
