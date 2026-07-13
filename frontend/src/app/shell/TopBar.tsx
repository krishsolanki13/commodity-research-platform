import { Sun, Moon, AlignJustify, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useWorkspace } from '@/stores/workspace'
import { cn } from '@/lib/cn'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/ui/tooltip'
import { client } from '@/api/client'
import { Kbd } from '@/ui/Kbd'

interface TopBarProps {
  onOpenPalette: () => void
}

export function TopBar({ onOpenPalette }: TopBarProps) {
  const { theme, density, setTheme, setDensity } = useWorkspace()

  const { data: health, isError, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: () => client.get<{ status: string }>('/api/health'),
    staleTime: 0,
    refetchInterval: 30_000,
    retry: 0,
  })

  const healthColor = isPending
    ? 'bg-text-disabled'
    : isError || health?.status !== 'ok'
      ? 'bg-crit'
      : 'bg-ok'

  const healthLabel = isPending
    ? 'Checking API...'
    : isError || health?.status !== 'ok'
      ? 'API unreachable — is `make dev` running?'
      : 'API healthy'

  return (
    <TooltipProvider delayDuration={300}>
      <header className="flex h-12 shrink-0 items-center border-b border-border-default bg-bg-panel px-4 z-40">
        <span className="text-lg font-semibold text-text-emphasis">
          Commodity Research
        </span>

        <div className="mx-auto flex-1 px-8 max-w-lg">
          <button
            onClick={onOpenPalette}
            className="flex w-full items-center gap-2 rounded-md border border-border-default bg-bg-app px-3 py-1.5 text-sm text-text-secondary hover:border-border-strong hover:text-text-primary transition-colors duration-fast"
          >
            <Search size={14} strokeWidth={1.75} />
            <span className="flex-1 text-left">Search or jump to...</span>
            <Kbd>⌘K</Kbd>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger>
              <span
                aria-label={healthLabel}
                className={cn('block h-2 w-2 rounded-full', healthColor)}
              />
            </TooltipTrigger>
            <TooltipContent side="bottom">{healthLabel}</TooltipContent>
          </Tooltip>

          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            className="rounded-sm p-1.5 text-text-secondary hover:bg-bg-hover hover:text-text-primary"
          >
            {theme === 'dark'
              ? <Sun size={16} strokeWidth={1.75} />
              : <Moon size={16} strokeWidth={1.75} />
            }
          </button>

          <button
            onClick={() =>
              setDensity(density === 'compact' ? 'comfortable' : 'compact')
            }
            aria-label={`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} density`}
            className="rounded-sm p-1.5 text-text-secondary hover:bg-bg-hover hover:text-text-primary"
          >
            <AlignJustify size={16} strokeWidth={1.75} />
          </button>
        </div>
      </header>
    </TooltipProvider>
  )
}
