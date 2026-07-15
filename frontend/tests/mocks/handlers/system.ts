import { http, HttpResponse } from 'msw'
import { dataStatusFixture } from '../fixtures/data-status'

export const systemHandlers = [
  http.get('http://localhost:8000/api/system/data-status', () =>
    HttpResponse.json(dataStatusFixture)
  ),

  http.post('http://localhost:8000/api/system/ingest', () =>
    HttpResponse.json({
      status: 'ok',
      assets_ingested: ['gold', 'silver', 'copper', 'wti', 'brent', 'natural_gas'],
      assets_failed: [],
      detail: null,
    })
  ),
]
