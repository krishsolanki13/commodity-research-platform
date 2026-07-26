import { Sun, Moon, AlignJustify } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useWorkspace } from '@/stores/workspace'
import { cn } from '@/lib/cn'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'
import { client } from '@/api/client'

interface TopBarProps {
  onOpenPalette: () => void
}

export function TopBar({ onOpenPalette: _onOpenPalette }: TopBarProps) {
  const { theme, density, setTheme, setDensity } = useWorkspace()

  const {
    data: health,
    isError,
    isPending,
  } = useQuery({
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
      <header className="h-12 z-40 flex shrink-0 items-center border-b border-border-default bg-bg-panel px-4">
        <span className="text-lg font-semibold text-text-emphasis">Commodity Research</span>

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
            className="p-1.5 rounded-sm text-text-secondary hover:bg-bg-hover hover:text-text-primary"
          >
            {theme === 'dark' ? (
              <Sun size={16} strokeWidth={1.75} />
            ) : (
              <Moon size={16} strokeWidth={1.75} />
            )}
          </button>

          <button
            onClick={() => setDensity(density === 'compact' ? 'comfortable' : 'compact')}
            aria-label={`Switch to ${density === 'compact' ? 'comfortable' : 'compact'} density`}
            className="p-1.5 rounded-sm text-text-secondary hover:bg-bg-hover hover:text-text-primary"
          >
            <AlignJustify size={16} strokeWidth={1.75} />
          </button>
        </div>
      </header>
    </TooltipProvider>
  )
}
