import { cn } from '@/lib/cn'
import type { components } from '@/api/schema'

type StrategyMeta = components['schemas']['StrategyMeta']

interface StrategyPickerProps {
  strategies: StrategyMeta[]
  value: string | null
  onChange: (value: string) => void
  className?: string
}

export function StrategyPicker({ strategies, value, onChange, className }: StrategyPickerProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {strategies.map((strategy) => {
        const isActive = value === strategy.name
        return (
          <button
            key={strategy.name}
            type="button"
            data-active={isActive ? 'true' : undefined}
            aria-pressed={isActive}
            onClick={() => onChange(strategy.name)}
            className={cn(
              'relative rounded-sm border border-border-default px-3 py-2 text-left',
              'transition-colors duration-fast hover:bg-bg-hover',
              isActive && 'border-l-2 border-l-accent bg-bg-selected pl-[10px]'
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
      })}
    </div>
  )
}
