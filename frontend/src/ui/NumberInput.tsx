import { cn } from '@/lib/cn'

interface NumberInputProps {
  value: number | ''
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
  unit?: string
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function NumberInput({
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  disabled,
  placeholder,
  className,
}: NumberInputProps) {
  return (
    <div className="relative flex items-center">
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        placeholder={placeholder}
        className={cn(
          'h-[var(--input-height)] w-full rounded-sm border border-border-strong bg-bg-app',
          'px-3 font-mono text-sm text-text-primary',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'focus-visible:ring-offset-1 focus-visible:ring-offset-bg-app',
          'disabled:cursor-not-allowed disabled:opacity-50',
          '[appearance:textfield]',
          '[&::-webkit-inner-spin-button]:appearance-none',
          '[&::-webkit-outer-spin-button]:appearance-none',
          unit && 'pr-12',
          className
        )}
      />
      {unit && (
        <span className="pointer-events-none absolute right-3 text-xs text-text-secondary">
          {unit}
        </span>
      )}
    </div>
  )
}
