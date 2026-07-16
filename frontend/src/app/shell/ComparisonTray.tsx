import { useComparisonBasket } from '@/stores/comparisonBasket'
import { useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import { Separator } from '@/ui/separator'
import { cn } from '@/lib/cn'

export function ComparisonTray() {
  const { ids, clear } = useComparisonBasket()
  const navigate = useNavigate()

  if (ids.length === 0) return null

  function handleCompare() {
    void navigate(`/runs/compare?ids=${ids.join(',')}`)
  }

  return (
    <div
      role="complementary"
      aria-label="Comparison basket"
      className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2"
    >
      <div className="flex items-center gap-2 rounded-full border border-border-strong bg-bg-raised px-4 py-2 shadow-overlay">
        <span className="font-mono text-sm font-medium text-text-emphasis">
          {ids.length} {ids.length === 1 ? 'run' : 'runs'} selected
        </span>
        <Separator orientation="vertical" className="h-4" />
        <button
          onClick={handleCompare}
          disabled={ids.length < 2}
          aria-disabled={ids.length < 2}
          className={cn(
            'text-sm font-medium transition-colors duration-fast',
            ids.length >= 2
              ? 'text-text-accent hover:text-accent-hover'
              : 'cursor-not-allowed text-text-disabled'
          )}
          title={
            ids.length < 2
              ? 'Select at least 2 runs to compare'
              : 'Compare selected runs'
          }
        >
          Compare →
        </button>
        <button
          onClick={clear}
          aria-label="Clear selection"
          className="text-text-secondary hover:text-text-primary"
        >
          <X size={14} strokeWidth={1.75} />
        </button>
      </div>
      {ids.length === 1 && (
        <span className="text-xs text-text-secondary pr-1">
          Select 1 more run to compare
        </span>
      )}
    </div>
  )
}
