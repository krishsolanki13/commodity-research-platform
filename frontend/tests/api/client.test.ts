import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'
import { client, ApiClientError } from '@/api/client'

const server = setupServer(
  http.get('http://localhost:8000/api/health', () =>
    HttpResponse.json({ status: 'ok', version: '0.1.0', backend_tests: 267 })
  ),
  http.get('http://localhost:8000/api/assets/unknown/ohlcv', () =>
    HttpResponse.json(
      { error: { code: 'ASSET_NOT_FOUND', message: "Asset 'unknown' is not in the universe." } },
      { status: 404 }
    )
  ),
  http.post('http://localhost:8000/api/signals/evaluate', () =>
    HttpResponse.json(
      {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Invalid parameters.',
          field_errors: { fast_period: 'Must be less than slow_period.' },
        },
      },
      { status: 400 }
    )
  ),
  http.get('http://localhost:8000/api/runs/broken', () =>
    HttpResponse.json(
      { error: { code: 'INTERNAL', message: 'Unexpected error.' } },
      { status: 500 }
    )
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('client', () => {
  it('returns typed response on successful GET', async () => {
    const data = await client.get<{ status: string; version: string }>('/api/health')
    expect(data.status).toBe('ok')
    expect(data.version).toBe('0.1.0')
  })

  it('throws ApiClientError with code and status on 404', async () => {
    try {
      await client.get('/api/assets/unknown/ohlcv')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiClientError)
      expect((e as ApiClientError).apiError.code).toBe('ASSET_NOT_FOUND')
      expect((e as ApiClientError).apiError.status).toBe(404)
    }
  })

  it('throws ApiClientError with fieldErrors on 400', async () => {
    try {
      await client.post('/api/signals/evaluate', {})
    } catch (e) {
      expect(e).toBeInstanceOf(ApiClientError)
      expect((e as ApiClientError).apiError.status).toBe(400)
      expect((e as ApiClientError).apiError.fieldErrors).toHaveProperty('fast_period')
    }
  })

  it('throws ApiClientError with code INTERNAL on 500', async () => {
    try {
      await client.get('/api/runs/broken')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiClientError)
      expect((e as ApiClientError).apiError.status).toBe(500)
      expect((e as ApiClientError).apiError.code).toBe('INTERNAL')
    }
  })

  it('throws NETWORK_ERROR when fetch itself fails', async () => {
    server.use(http.get('http://localhost:8000/api/network-fail', () => HttpResponse.error()))
    try {
      await client.get('/api/network-fail')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiClientError)
      expect((e as ApiClientError).apiError.code).toBe('NETWORK_ERROR')
    }
  })

  it('parses FastAPI HTTPException detail.code (INSUFFICIENT_CURVE_COVERAGE)', async () => {
    server.use(
      http.post('http://localhost:8000/api/signals/evaluate-async', () =>
        HttpResponse.json(
          {
            detail: {
              code: 'INSUFFICIENT_CURVE_COVERAGE',
              message:
                'Requested window starts 2015-01-01, but curve data for gold is only available from 2024-09-27 onward.',
              curve_coverage_start: '2024-09-27',
            },
          },
          { status: 400 }
        )
      )
    )
    try {
      await client.post('/api/signals/evaluate-async', {})
      expect.fail('expected throw')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiClientError)
      expect((e as ApiClientError).apiError.code).toBe('INSUFFICIENT_CURVE_COVERAGE')
      expect((e as ApiClientError).apiError.detail).toBe('2024-09-27')
    }
  })
})
