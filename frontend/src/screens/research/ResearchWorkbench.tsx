import { useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { safeJsonParse } from '@/lib/json'
import { useEvaluateChainMutation } from '@/api/hooks/useEvaluateChainMutation'
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

export default function ResearchWorkbenchScreen() {
  const [searchParams] = useSearchParams()
  const [evaluationResult, setEvaluationResult] = useState<WorkbenchEvaluationResult | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [evaluateProgress, setEvaluateProgress] = useState<EvaluateProgress | null>(null)
  const [lastEvaluatedConfigHash, setLastEvaluatedConfigHash] = useState<string | null>(null)
  const [canEvaluate, setCanEvaluate] = useState(false)
  const [evaluateReason, setEvaluateReason] = useState<string | null>(null)

  // Ref to trigger evaluate from the button in the right half, while all param
  // building logic stays inside WorkbenchConfigRail.
  const evaluateTriggerRef = useRef<(() => void) | null>(null)

  // R-Q7: onProgress is a hook parameter — mutateAsync receives only serializable params
  const evaluateChain = useEvaluateChainMutation((progress) => setEvaluateProgress(progress))

  const asset = searchParams.get('asset') ?? ''
  const strategy = searchParams.get('strategy') ?? ''
  const paramsJson = searchParams.get('params') ?? '{}'
  const featuresJson = searchParams.get('features') ?? '[]'
  const fromDate = searchParams.get('from_date') ?? '2015-01-01'
  const toDate = searchParams.get('to_date') ?? new Date().toISOString().slice(0, 10)

  // R-Q8: safeJsonParse from '@/lib/json'
  const parsedParams = safeJsonParse<Record<string, unknown>>(paramsJson, {})
  const parsedFeatures = safeJsonParse<FeatureSpecRequest[]>(featuresJson, [])

  const progressLabel =
    evaluateProgress?.stepIndex === 1
      ? 'Computing features...'
      : evaluateProgress?.stepIndex === 2
        ? 'Generating signal...'
        : evaluateProgress?.stepIndex === 3
          ? 'Evaluating signal...'
          : 'Evaluating...'

  async function handleEvaluate(p: EvaluateParams) {
    const configHash = JSON.stringify({
      asset: p.asset,
      strategy: p.strategy,
      params: p.params,
      featureSpecs: p.featureSpecs,
      fromDate: p.fromDate,
      toDate: p.toDate,
    })
    setEvaluating(true)
    setEvaluateProgress(null)
    try {
      const result = await evaluateChain.mutateAsync({
        asset: p.asset,
        strategy: p.strategy,
        params: p.params,
        featureSpecs: p.featureSpecs,
        fromDate: p.fromDate,
        toDate: p.toDate,
      })
      setEvaluationResult(result)
      setLastEvaluatedConfigHash(configHash)
    } catch (e) {
      console.error('Evaluate chain failed:', e)
    } finally {
      setEvaluating(false)
      setEvaluateProgress(null)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Title — fixed, does not scroll */}
      <div className="shrink-0 px-6 pt-6 pb-4">
        <h1 className="text-xl font-semibold text-text-primary">Research Workbench</h1>
      </div>

      <div className="flex min-h-0 flex-1 gap-6 overflow-hidden px-6 pb-6">
        {/* Left rail — scrolls independently */}
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
        />

        {/* Right half */}
        <div className="relative flex flex-1 flex-col overflow-hidden pt-4">
          <Panel title="Evaluate" padding={false}>
            <div className="flex flex-col gap-4 p-4">
              <Button
                variant="primary"
                disabled={!canEvaluate || evaluating}
                onClick={() => evaluateTriggerRef.current?.()}
                className="w-full"
              >
                {evaluating ? progressLabel : 'Evaluate signal'}
              </Button>
              {evaluateReason && !evaluating && (
                <p className="text-xs text-text-secondary">{evaluateReason}</p>
              )}
            </div>
          </Panel>

          <div className="flex-1 overflow-y-auto mt-4">
            <WorkbenchEvidenceCanvas
              asset={asset}
              strategy={strategy}
              params={parsedParams}
              featureSpecs={parsedFeatures}
              fromDate={fromDate}
              toDate={toDate}
              lastEvaluatedConfigHash={lastEvaluatedConfigHash}
              evaluationResult={evaluationResult}
            />
          </div>
        </div>
      </div>

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
