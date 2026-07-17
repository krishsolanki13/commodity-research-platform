import { http, HttpResponse } from 'msw'
import {
  curveAvailableFixture,
  goldCurveSnapshotFixture,
  goldCurveHistoryFixture,
} from '../fixtures/curve'

// NOTE: Endpoint paths below are assumed from the spec.
// Cursor Step 1 must verify actual paths from the F0 OpenAPI spec:
//   curl -sf http://localhost:8000/openapi.json | python3 -c "
//   import sys, json; spec = json.load(sys.stdin)
//   print([p for p in spec['paths'] if 'curve' in p.lower()])"
// If actual paths differ, update both here AND in the hook files.

export const curveHandlers = [
  http.get('http://localhost:8000/api/curves/available', () =>
    HttpResponse.json(curveAvailableFixture)
  ),
  http.get('http://localhost:8000/api/curves/gold/snapshot', () =>
    HttpResponse.json(goldCurveSnapshotFixture)
  ),
  http.get('http://localhost:8000/api/curves/:asset/snapshot', ({ params }) =>
    HttpResponse.json({ ...goldCurveSnapshotFixture, asset: params.asset as string })
  ),
  http.get('http://localhost:8000/api/curves/gold/history', () =>
    HttpResponse.json(goldCurveHistoryFixture)
  ),
  http.get('http://localhost:8000/api/curves/:asset/history', ({ params }) =>
    HttpResponse.json({ ...goldCurveHistoryFixture, asset: params.asset as string })
  ),
]
