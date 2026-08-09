import { cn } from '@/lib/cn'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'
import type { components } from '@/api/schema'

type StrategyMeta = components['schemas']['StrategyMeta']

interface StrategyPickerProps {
  strategies: StrategyMeta[]
  value: string | null
  onChange: (value: string) => void
  /** Selected asset — used to disable wti_brent_spread when not WTI */
  asset?: string | null
  className?: string
}

export function isStrategyDisabled(strategyName: string, asset: string | null | undefined) {
  return strategyName === 'wti_brent_spread' && asset !== 'wti'
}

export function StrategyPicker({
  strategies,
  value,
  onChange,
  asset = null,
  className,
}: StrategyPickerProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {strategies.map((strategy) => {
        const isActive = value === strategy.name
        const disabled = isStrategyDisabled(strategy.name, asset)

        const card = (
          <button
            type="button"
            data-active={isActive ? 'true' : undefined}
            data-disabled={disabled ? 'true' : undefined}
            aria-pressed={isActive}
            aria-disabled={disabled}
            onClick={() => {
              if (disabled) return
              onChange(strategy.name)
            }}
            className={cn(
              'relative w-full rounded-sm border border-border-default px-3 py-2 text-left',
              'transition-colors duration-fast hover:bg-bg-hover',
              isActive && 'border-l-2 border-l-accent bg-bg-selected pl-[10px]',
              disabled && 'cursor-not-allowed opacity-50 hover:bg-transparent'
            )}
          >
            <p className="text-sm font-semibold text-text-primary">{strategy.display_name}</p>
            <p
              className={cn(
                'mt-0.5 text-xs',
                isActive ? 'text-text-primary' : 'text-text-secondary'
              )}
            >
              {strategy.description}
            </p>
          </button>
        )

        if (!disabled) {
          return (
            <div key={strategy.name}>{card}</div>
          )
        }

        return (
          <TooltipProvider key={strategy.name} delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="block w-full">{card}</span>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[220px] text-xs">
                WTI-Brent spread requires WTI as the primary asset
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )
      })}
    </div>
  )
}
