import { http, HttpResponse } from 'msw'
import { indicatorCatalogFixture } from '../fixtures/indicators'
import { strategyCatalogFixture } from '../fixtures/strategies'

export const indicatorHandlers = [
  http.get('http://localhost:8000/api/indicators', () =>
    HttpResponse.json(indicatorCatalogFixture)
  ),
  http.get('http://localhost:8000/api/strategies', () => HttpResponse.json(strategyCatalogFixture)),
]
