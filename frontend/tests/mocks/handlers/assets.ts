import { http, HttpResponse } from 'msw'
import { universeFixture } from '../fixtures/universe'
import { goldOhlcvFixture } from '../fixtures/gold-ohlcv'

export const assetHandlers = [
  http.get('http://localhost:8000/api/assets', () => HttpResponse.json(universeFixture)),

  // Specific routes before generic :asset handler — MSW matches in registration order
  http.get('http://localhost:8000/api/assets/gold/ohlcv', () =>
    HttpResponse.json(goldOhlcvFixture)
  ),

  http.get('http://localhost:8000/api/assets/gold/summary', () =>
    HttpResponse.json(universeFixture.summaries.gold)
  ),

  http.get('http://localhost:8000/api/assets/notanasset/ohlcv', () =>
    HttpResponse.json(
      { error: { code: 'ASSET_NOT_FOUND', message: "Asset 'notanasset' is not in the universe." } },
      { status: 404 }
    )
  ),

  http.get('http://localhost:8000/api/assets/notanasset/summary', () =>
    HttpResponse.json(
      { error: { code: 'ASSET_NOT_FOUND', message: "Asset 'notanasset' is not in the universe." } },
      { status: 404 }
    )
  ),

  http.get('http://localhost:8000/api/assets/:asset/ohlcv', ({ params }) =>
    HttpResponse.json({ ...goldOhlcvFixture, asset: params.asset as string })
  ),

  http.get('http://localhost:8000/api/assets/:asset/summary', ({ params }) => {
    const assetName = params.asset as string
    const summary = (universeFixture.summaries as Record<string, unknown>)[assetName]
    if (!summary) {
      return HttpResponse.json(
        { error: { code: 'ASSET_NOT_FOUND', message: `Asset '${assetName}' not found.` } },
        { status: 404 }
      )
    }
    return HttpResponse.json(summary)
  }),
]
