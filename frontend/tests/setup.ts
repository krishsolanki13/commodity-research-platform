import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { setupServer } from 'msw/node'
import { handlers } from './mocks/handlers/index'

// --- ECharts global mock ---
// jsdom has no canvas support. ECharts calls canvas.getContext('2d') on init, which
// throws in jsdom without this mock. Tests verify component shell behavior only.
// Visual correctness is verified in F8 Playwright tests with a real browser.
export const mockChartInstance = {
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  dispatchAction: vi.fn(),
  getDataURL: vi.fn(() => 'data:image/png;base64,iVBORw0KGgo='),
  group: '',
}

vi.mock('@/lib/echarts-setup', () => ({
  echarts: {
    init: vi.fn(() => mockChartInstance),
    connect: vi.fn(),
    disconnect: vi.fn(),
    use: vi.fn(),
  },
}))

// --- URL object mock ---
// Required for file download tests: PNG export (ChartFrame), CSV export (DataGrid),
// artifact downloads (F6+). Defined once here to prevent duplication across test files.
Object.defineProperty(URL, 'createObjectURL', {
  writable: true,
  value: vi.fn(() => 'blob:mock-url'),
})
Object.defineProperty(URL, 'revokeObjectURL', {
  writable: true,
  value: vi.fn(),
})

// ─── MSW Global Server ────────────────────────────────────────────────────────
// Shared across all hook and screen tests.
// Individual test files add scenario overrides via server.use(...) inside the test.
// afterEach resets back to the base handlers.

export const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
