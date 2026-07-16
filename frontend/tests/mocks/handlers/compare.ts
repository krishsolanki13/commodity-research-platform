import { http, HttpResponse } from 'msw'
import { compareFixture } from '../fixtures/compare'

export const compareHandlers = [
  http.post('http://localhost:8000/api/runs/compare', () =>
    HttpResponse.json(compareFixture)
  ),
  http.delete('http://localhost:8000/api/runs/:runId', ({ params }) =>
    HttpResponse.json({ deleted: true, run_id: params.runId })
  ),
]
