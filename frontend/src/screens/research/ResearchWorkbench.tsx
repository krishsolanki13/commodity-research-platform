import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { safeJsonParse } from '@/lib/json'
import { ApiClientError } from '@/api/client'
import { qk } from '@/api/queryKeys'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'
import {
  useEvaluateChainMutation,
  isEvaluateChainAsyncLaunch,
} from '@/api/hooks/useEvaluateChainMutation'
import { useEvaluateAsyncStatus, useEvaluateAsyncResult } from '@/api/hooks/useEvaluateAsync'
import { LoadingSkeleton } from '@/components/layout/LoadingSkeleton'
import {
  WorkbenchConfigRail,
  type EvaluateParams,
  type EvaluateProgress,
} from '@/features/research/WorkbenchConfigRail'
import {
  WorkbenchEvidenceCanvas,
  type WorkbenchEvaluationResult,
} from '@/features/research/WorkbenchEvidenceCanvas'
import { WorkbenchICGateStrip } from '@/features/research/WorkbenchICGateStrip'
import { Panel } from '@/ui/Panel'
import { Button } from '@/ui/button'
import type { components } from '@/api/schema'

type FeatureSpecRequest = components['schemas']['FeatureSpecRequest']
type FeatureComputeResponse = components['schemas']['FeatureComputeResponse']
type SignalGenerateResponse = components['schemas']['SignalGenerateResponse']

interface PendingAsyncChain {
  features: FeatureComputeResponse
  signal: SignalGenerateResponse
  configHash: string
  asset: string
  strategy: string
  params: Record<string, unknown>
}

function coverageBoundaryDate(e: ApiClientError): string | null {
  if (e.apiError.detail && /^\d{4}-\d{2}-\d{2}$/.test(e.apiError.detail)) {
    return e.apiError.detail
  }
  const dates = `${e.apiError.message} ${e.apiError.detail ?? ''}`.match(/\d{4}-\d{2}-\d{2}/g)
  return dates?.[dates.length - 1] ?? null
}

function formatEvalError(
  e: unknown,
  failedStep: EvaluateProgress['step'] | null,
  asset?: string,
): string {
  if (e instanceof ApiClientError && e.apiError.code === 'INSUFFICIENT_CURVE_COVERAGE') {
    const boundary = coverageBoundaryDate(e) ?? 'the coverage start'
    return `Curve data for ${asset || 'this asset'} starts ${boundary} — adjust date range`
  }

  const detail =
    e instanceof ApiClientError
      ? e.apiError.detail
        ? `${e.message} — ${e.apiError.detail}`
        : e.message
      : e instanceof Error
        ? e.message
        : 'Unknown error — check API logs'

  const stageLabel =
    failedStep === 'features'
      ? 'Feature computation failed'
      : failedStep === 'signal'
        ? 'Signal generation failed'
        : failedStep === 'evaluation'
          ? 'Signal evaluation failed'
          : 'Signal evaluation failed'

  return `${stageLabel}: ${detail}`
}

export default function ResearchWorkbenchScreen() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [evaluationResult, setEvaluationResult] = useState<WorkbenchEvaluationResult | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [evaluateProgress, setEvaluateProgress] = useState<EvaluateProgress | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)
  const [lastEvaluatedConfigHash, setLastEvaluatedConfigHash] = useState<string | null>(null)
  const [canEvaluate, setCanEvaluate] = useState(false)
  const [evaluateReason, setEvaluateReason] = useState<string | null>(null)
  const [hasEvaluated, setHasEvaluated] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [asyncJobId, setAsyncJobId] = useState<string | null>(null)

  // Ref to trigger evaluate from the button in the right half, while all param
  // building logic stays inside WorkbenchConfigRail.
  const evaluateTriggerRef = useRef<(() => void) | null>(null)
  const progressRef = useRef<EvaluateProgress | null>(null)
  const pendingAsyncRef = useRef<PendingAsyncChain | null>(null)

  // R-Q7: onProgress is a hook parameter — mutateAsync receives only serializable params
  const evaluateChain = useEvaluateChainMutation((progress) => {
    progressRef.current = progress
    setEvaluateProgress(progress)
  })

  const asset = searchParams.get('asset') ?? ''
  const strategy = searchParams.get('strategy') ?? ''
  const paramsJson = searchParams.get('params') ?? '{}'
  const featuresJson = searchParams.get('features') ?? '[]'
  const fromDate = searchParams.get('from_date') ?? '2015-01-01'
  const toDate = searchParams.get('to_date') ?? new Date().toISOString().slice(0, 10)

  // R-Q8: safeJsonParse from '@/lib/json'
  const parsedParams = safeJsonParse<Record<string, unknown>>(paramsJson, {})
  const parsedFeatures = safeJsonParse<FeatureSpecRequest[]>(featuresJson, [])

  const { data: asyncStatus, isError: asyncStatusIsError, error: asyncStatusError } =
    useEvaluateAsyncStatus(asyncJobId)
  const asyncComplete = asyncStatus?.status === 'complete'
  const {
    data: asyncEvalResult,
    isError: asyncResultIsError,
    error: asyncResultError,
  } = useEvaluateAsyncResult(asyncJobId, asyncComplete)

  const { data: ohlcvData, isLoading: ohlcvLoading } = useAssetOhlcv(asset, {
    from_date: fromDate,
    to_date: toDate,
    downsample: 'view',
  })
  const ohlcvLoaded = !!ohlcvData?.data?.index && ohlcvData.data.index.length > 0
  // Wait for OHLCV to settle so results view never opens on a blank chart.
  // Empty/error responses still switch (canvas shows empty state) — don't trap.
  const showResults = hasEvaluated && (ohlcvLoaded || !ohlcvLoading)

  useEffect(() => {
    if (!evaluating) {
      setElapsed(0)
      return
    }
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(interval)
  }, [evaluating])

  // Reset to config view when asset or strategy changes — not on param-only changes
  useEffect(() => {
    setHasEvaluated(false)
    setEvaluationResult(null)
    setLastEvaluatedConfigHash(null)
    setEvalError(null)
    setEvaluating(false)
    setAsyncJobId(null)
    pendingAsyncRef.current = null
  }, [asset, strategy])

  useEffect(() => {
    if (!asyncJobId) return
    if (asyncStatus?.status !== 'failed' && !asyncStatusIsError) return
    const err =
      asyncStatusIsError && asyncStatusError
        ? asyncStatusError
        : new Error(asyncStatus?.error ?? 'Async evaluation failed')
    setEvalError(formatEvalError(err, 'evaluation', asset))
    setEvaluationResult(null)
    setHasEvaluated(false)
    setEvaluating(false)
    setEvaluateProgress(null)
    setAsyncJobId(null)
    pendingAsyncRef.current = null
  }, [asyncJobId, asyncStatus, asyncStatusIsError, asyncStatusError, asset])

  useEffect(() => {
    if (!asyncJobId || asyncStatus?.status !== 'complete') return
    if (asyncResultIsError) {
      setEvalError(formatEvalError(asyncResultError, 'evaluation', asset))
      setEvaluationResult(null)
      setHasEvaluated(false)
      setEvaluating(false)
      setEvaluateProgress(null)
      setAsyncJobId(null)
      pendingAsyncRef.current = null
      return
    }
    if (!asyncEvalResult || !pendingAsyncRef.current) return
    const pending = pendingAsyncRef.current
    queryClient.setQueryData(
      qk.signalEvaluate(pending.asset, pending.strategy, pending.params),
      asyncEvalResult,
    )
    setEvaluationResult({
      features: pending.features,
      signal: pending.signal,
      evaluation: asyncEvalResult,
      evaluatedAt: new Date().toISOString(),
    })
    setLastEvaluatedConfigHash(pending.configHash)
    setHasEvaluated(true)
    setEvaluating(false)
    setEvaluateProgress(null)
    setAsyncJobId(null)
    pendingAsyncRef.current = null
  }, [
    asyncJobId,
    asyncStatus?.status,
    asyncEvalResult,
    asyncResultIsError,
    asyncResultError,
    queryClient,
    asset,
  ])

  const progressLabel =
    evaluateProgress?.stepIndex === 1
      ? 'Computing features...'
      : evaluateProgress?.stepIndex === 2
        ? 'Generating signal...'
        : evaluateProgress?.stepIndex === 3
          ? 'Evaluating signal...'
          : 'Evaluating...'

  const showQueued =
    evaluating &&
    strategy === 'carry' &&
    asyncStatus?.status !== 'running' &&
    asyncStatus?.status !== 'complete'

  async function handleEvaluate(p: EvaluateParams) {
    const configHash = JSON.stringify({
      asset: p.asset,
      strategy: p.strategy,
      params: paramsJson,
      features: featuresJson,
      fromDate: p.fromDate,
      toDate: p.toDate,
    })
    setEvaluating(true)
    setEvaluateProgress(null)
    progressRef.current = null
    setEvalError(null)
    setAsyncJobId(null)
    pendingAsyncRef.current = null
    let launchedAsync = false
    try {
      const result = await evaluateChain.mutateAsync({
        asset: p.asset,
        strategy: p.strategy,
        params: p.params,
        featureSpecs: p.featureSpecs,
        fromDate: p.fromDate,
        toDate: p.toDate,
      })
      if (isEvaluateChainAsyncLaunch(result)) {
        pendingAsyncRef.current = {
          features: result.features,
          signal: result.signal,
          configHash,
          asset: p.asset,
          strategy: p.strategy,
          params: p.params,
        }
        setAsyncJobId(result.job_id)
        launchedAsync = true
        return
      }
      setEvaluationResult(result)
      setLastEvaluatedConfigHash(configHash)
      setHasEvaluated(true)
    } catch (e) {
      console.error('Evaluate chain failed:', e)
      setEvalError(formatEvalError(e, (progressRef.current as EvaluateProgress | null)?.step ?? null, asset))
      setEvaluationResult(null)
      setHasEvaluated(false)
    } finally {
      if (!launchedAsync) {
        setEvaluating(false)
        setEvaluateProgress(null)
      }
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Title — fixed, does not scroll */}
      <div className="shrink-0 px-6 pb-4 pt-6">
        <h1 className="text-xl font-semibold text-text-primary">Research Workbench</h1>
      </div>

      {!showResults ? (
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-6 overflow-hidden px-6 pb-6">
          <div className="min-h-0 overflow-y-auto">
            <WorkbenchConfigRail
              onEvaluate={(p) => {
                void handleEvaluate(p)
              }}
              onCanEvaluateChange={(can, reason) => {
                setCanEvaluate(can)
                setEvaluateReason(reason)
              }}
              onEvaluateReady={(trigger) => {
                evaluateTriggerRef.current = trigger
              }}
              evalError={evalError}
            />
          </div>

          <div className="min-h-0 overflow-y-auto">
            <Panel title="Evaluate">
              <div className="flex flex-col gap-3">
                <Button
                  variant="primary"
                  disabled={!canEvaluate || evaluating}
                  onClick={() => evaluateTriggerRef.current?.()}
                  className="w-full"
                >
                  {evaluating ? progressLabel : 'Evaluate signal'}
                </Button>
                {evaluating && (
                  <div className="font-mono text-sm text-text-secondary">
                    {showQueued ? 'Queued...' : `Evaluating... ${elapsed}s`}
                  </div>
                )}
                {hasEvaluated && !evaluating && !ohlcvLoaded && ohlcvLoading && (
                  <div className="flex flex-col gap-2">
                    <p className="font-mono text-sm text-text-secondary">Loading chart data...</p>
                    <LoadingSkeleton variant="chart" />
                  </div>
                )}
                {evaluateReason && !evaluating && (
                  <p className="text-xs text-text-secondary">{evaluateReason}</p>
                )}
                {!evaluating && !hasEvaluated && (
                  <p className="text-xs text-text-secondary">
                    Assemble features and a signal, then click Evaluate. Evaluation must precede
                    backtesting.
                  </p>
                )}
              </div>
            </Panel>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6">
          <button
            type="button"
            onClick={() => setHasEvaluated(false)}
            className="gap-1.5 flex w-fit items-center text-sm text-text-secondary transition-colors hover:text-text-primary"
          >
            ← Modify signal
          </button>

          <WorkbenchEvidenceCanvas
            asset={asset}
            strategy={strategy}
            params={parsedParams}
            featureSpecs={parsedFeatures}
            fromDate={fromDate}
            toDate={toDate}
            lastEvaluatedConfigHash={lastEvaluatedConfigHash}
            evaluationResult={evaluationResult}
            evaluating={evaluating}
          />
        </div>
      )}

      <div className="shrink-0 border-t border-border-default">
        <WorkbenchICGateStrip
          evaluation={evaluationResult?.evaluation.evaluation ?? null}
          evaluating={evaluating}
          asset={asset}
          strategy={strategy}
          paramsJson={paramsJson}
        />
      </div>
    </div>
  )
}
