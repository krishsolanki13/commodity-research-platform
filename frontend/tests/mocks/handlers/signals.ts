import { http, HttpResponse } from 'msw'
import { goldEmaEvalFixture } from '../fixtures/signal-eval'
import type { components } from '@/api/schema'

type SignalGenerateResponse = components['schemas']['SignalGenerateResponse']

// Synthetic 3-bar signal for testing — epoch-ms indices (correct per backend fix)
const goldSignalFixture: SignalGenerateResponse = {
  asset: 'gold',
  strategy: 'ema_crossover',
  params: { fast_period: 50, slow_period: 200, signal_threshold: 0.0 },
  bars: 3,
  raw_signal: {
    index: [1609459200000, 1609545600000, 1609632000000],
    columns: { raw: [0.5, -0.3, 0.8] },
  },
  position_signal: {
    index: [1609459200000, 1609545600000, 1609632000000],
    columns: { position: [1, -1, 1] },
  },
}

export const signalHandlers = [
  http.post('http://localhost:8000/api/signals/generate', () =>
    HttpResponse.json(goldSignalFixture)
  ),
  http.post('http://localhost:8000/api/signals/evaluate', () =>
    HttpResponse.json(goldEmaEvalFixture)
  ),
  http.post('http://localhost:8000/api/signals/evaluate-async', () =>
    HttpResponse.json({ job_id: 'eval-async-test-job', status: 'queued' }, { status: 202 })
  ),
  http.get('http://localhost:8000/api/signals/evaluate-async/:jobId/status', ({ params }) =>
    HttpResponse.json({ job_id: params.jobId, status: 'complete' })
  ),
  http.get('http://localhost:8000/api/signals/evaluate-async/:jobId/result', () =>
    HttpResponse.json(goldEmaEvalFixture)
  ),
]
