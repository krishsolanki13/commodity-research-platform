import { useNavigate } from 'react-router-dom'
import { TrendingUp, FlaskConical, Zap, Layers, Database } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Dialog, DialogContent } from '@/ui/dialog'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/ui/command'

interface NavEntry {
  label: string
  route: string
  icon: LucideIcon
}

const NAVIGATE_ITEMS: NavEntry[] = [
  { label: 'Market Overview', route: '/market', icon: TrendingUp },
  { label: 'Research Workbench', route: '/research', icon: FlaskConical },
  { label: 'Strategy Builder', route: '/backtest/new', icon: Zap },
  { label: 'Run Explorer', route: '/runs', icon: Layers },
  { label: 'Data Manager', route: '/system/data', icon: Database },
]

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()

  function handleSelect(route: string) {
    void navigate(route)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg border-border-strong bg-bg-raised p-0"
        aria-label="Command palette"
      >
        <Command>
          <CommandInput placeholder="Search commands and screens..." />
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigate">
            {NAVIGATE_ITEMS.map((item) => {
              const Icon = item.icon
              return (
                <CommandItem key={item.route} onSelect={() => handleSelect(item.route)}>
                  <Icon size={14} strokeWidth={1.75} className="mr-2 text-text-secondary" />
                  {item.label}
                </CommandItem>
              )
            })}
          </CommandGroup>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
