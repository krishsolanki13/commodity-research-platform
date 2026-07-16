import { http, HttpResponse } from 'msw'
import { runListFixture } from '../fixtures/run-list'

export const runHandlers = [
  http.get('http://localhost:8000/api/runs', () =>
    HttpResponse.json(runListFixture)
  ),
]
