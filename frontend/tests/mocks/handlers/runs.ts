import { http, HttpResponse } from 'msw'

export const runHandlers = [
  http.get('http://localhost:8000/api/runs', () =>
    HttpResponse.json({ runs: [], total: 0, page: 1, page_size: 5 })
  ),
]
