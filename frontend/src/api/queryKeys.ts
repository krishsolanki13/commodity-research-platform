export type SortField = 'sharpe' | 'max_drawdown' | 'total_return' | 'cagr' | 'executed_at'
export type SortOrder = 'asc' | 'desc'

export interface RunFilters {
  strategy?: string
  asset?: string
  sort?: SortField
  order?: SortOrder
  q?: string
  page?: number
  page_size?: number
}

export interface OhlcvParams {
  from_date?: string
  to_date?: string
  downsample?: 'view'
}

export const qk = {
  assets: () => ['assets'] as const,
  assetOhlcv: (asset: string, params: OhlcvParams = {}) =>
    ['assets', asset, 'ohlcv', params] as const,
  assetSummary: (asset: string, from?: string, to?: string) =>
    ['assets', asset, 'summary', { from, to }] as const,

  indicators: () => ['indicators'] as const,
  strategies: () => ['strategies'] as const,

  features: (asset: string, from: string | undefined, to: string | undefined, specs: unknown) =>
    ['features', 'compute', asset, { from, to, specs }] as const,
  signalGenerate: (asset: string, strategy: string, params: unknown) =>
    ['signals', 'generate', asset, strategy, params] as const,
  signalEvaluate: (asset: string, strategy: string, params: unknown) =>
    ['signals', 'evaluate', asset, strategy, params] as const,

  backtestStatus: (runId: string) => ['backtests', runId, 'status'] as const,

  runs: (filters: RunFilters = {}) => ['runs', filters] as const,
  run: (runId: string) => ['runs', runId] as const,
  runSeries: (runId: string, name: 'equity_curve' | 'pnl' | 'positions') =>
    ['runs', runId, 'series', name] as const,
  runTrades: (
    runId: string,
    page = 1,
    filters: { direction?: 'long' | 'short'; forceClosed?: boolean; pageSize?: number } = {}
  ) => ['runs', runId, 'trades', { page, ...filters }] as const,

  runCompare: (ids: string[]) => ['runs', 'compare', [...ids].sort()] as const,

  portfolioStatus: (runId: string) => ['portfolio', runId, 'status'] as const,
  portfolioSummary: (runId: string) => ['portfolio', runId, 'summary'] as const,
  portfolioRisk: (runId: string) => ['portfolio', runId, 'risk'] as const,
  portfolioCorrelation: (runId: string) => ['portfolio', runId, 'correlation'] as const,
  portfolioEquity: (runId: string) => ['portfolio', runId, 'equity'] as const,
  portfolioAssets: (runId: string) => ['portfolio', runId, 'assets'] as const,

  dataStatus: (asset?: string) => ['system', 'data-status', { asset }] as const,
  config: () => ['system', 'config'] as const,

  curveAvailable: () => ['curves', 'available'] as const,
  curveSnapshot: (asset: string, nContracts: number, observationDate?: string) =>
    ['curves', asset, 'snapshot', { nContracts, observationDate }] as const,
  curveHistory: (asset: string, from: string, to: string, nContracts: number) =>
    ['curves', asset, 'history', { from, to, nContracts }] as const,
} as const
