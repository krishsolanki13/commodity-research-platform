import * as React from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from '@/ui/button'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/ui/popover'

interface ComboboxOption {
  value: string
  label: string
  meta?: string
}

interface ComboboxProps {
  options: ComboboxOption[]
  value: string | null
  onChange: (value: string) => void
  placeholder?: string
  searchPlaceholder?: string
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

export function Combobox({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  searchPlaceholder = 'Search...',
  disabled,
  className,
  'aria-label': ariaLabel,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const selected = options.find((o) => o.value === value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={ariaLabel}
          disabled={disabled}
          className={cn('w-full justify-between', className)}
        >
          <span className={cn('truncate', !selected && !value && 'text-text-secondary')}>
            {selected ? selected.label : value ? value : placeholder}
          </span>
          <ChevronsUpDown
            size={14}
            strokeWidth={1.75}
            className="ml-2 shrink-0 text-text-secondary"
          />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="max-h-60 w-[var(--radix-popover-trigger-width)] overflow-y-auto p-0">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup>
            {options.map((option) => (
              <CommandItem
                key={option.value}
                value={option.value}
                onSelect={() => {
                  onChange(option.value)
                  setOpen(false)
                }}
              >
                <Check
                  size={14}
                  strokeWidth={1.75}
                  className={cn(
                    'mr-2 shrink-0',
                    value === option.value ? 'opacity-100' : 'opacity-0'
                  )}
                />
                <div className="flex flex-col gap-0.5">
                  <span className="font-medium text-text-primary">{option.label}</span>
                  {option.meta && (
                    <span className="text-xs text-text-secondary leading-snug">{option.meta}</span>
                  )}
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
