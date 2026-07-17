import { NavLink } from 'react-router-dom'
import {
  TrendingUp,
  FlaskConical,
  Zap,
  Layers,
  Globe,
  BarChart2,
  Database,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useWorkspace } from '@/stores/workspace'
import { cn } from '@/lib/cn'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/ui/tooltip'

interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  route: string
  phase: string | null
}

const NAV_ITEMS: NavItem[] = [
  { id: 'market', label: 'Market', icon: TrendingUp, route: '/market', phase: null },
  { id: 'research', label: 'Research', icon: FlaskConical, route: '/research', phase: null },
  { id: 'backtest', label: 'Backtest', icon: Zap, route: '/backtest/new', phase: null },
  { id: 'runs', label: 'Runs', icon: Layers, route: '/runs', phase: null },
  { id: 'intel', label: 'Intelligence', icon: Globe, route: '/intelligence', phase: null },
  { id: 'portfolio', label: 'Portfolio', icon: BarChart2, route: '/portfolio', phase: 'Phase 3' },
  { id: 'system', label: 'System', icon: Database, route: '/system/data', phase: null },
]

export function SidebarNav() {
  const { navCollapsed, toggleNavCollapsed } = useWorkspace()

  return (
    <TooltipProvider delayDuration={500}>
      <nav
        aria-label="Primary navigation"
        className={cn(
          'flex flex-col border-r border-border-default bg-bg-panel transition-[width] duration-base',
          navCollapsed ? 'w-14' : 'w-[232px]'
        )}
      >
        <ul role="list" className="flex-1 py-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon

            if (item.phase !== null) {
              return (
                <li key={item.id}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        aria-disabled="true"
                        className="flex cursor-not-allowed items-center gap-3 px-3 py-2 opacity-40"
                      >
                        <Icon
                          size={18}
                          strokeWidth={1.75}
                          className="shrink-0 text-text-secondary"
                        />
                        {!navCollapsed && (
                          <span className="text-sm text-text-secondary">{item.label}</span>
                        )}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>{item.phase} — coming soon</p>
                    </TooltipContent>
                  </Tooltip>
                </li>
              )
            }

            return (
              <li key={item.id} className="relative">
                <NavLink
                  to={item.route}
                  title={navCollapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2 text-sm transition-colors duration-fast',
                      'hover:bg-bg-hover hover:text-text-emphasis',
                      isActive
                        ? 'before:w-0.5 text-text-accent before:absolute before:left-0 before:top-0 before:h-full before:bg-accent'
                        : 'text-text-secondary'
                    )
                  }
                >
                  <Icon size={18} strokeWidth={1.75} className="shrink-0" />
                  {!navCollapsed && <span>{item.label}</span>}
                </NavLink>
              </li>
            )
          })}
        </ul>

        <div className="border-t border-border-default p-2">
          <button
            onClick={toggleNavCollapsed}
            aria-label={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            className="p-1.5 flex w-full items-center justify-center rounded-sm text-text-secondary hover:bg-bg-hover hover:text-text-primary"
          >
            {navCollapsed ? (
              <ChevronRight size={16} strokeWidth={1.75} />
            ) : (
              <ChevronLeft size={16} strokeWidth={1.75} />
            )}
          </button>
        </div>
      </nav>
    </TooltipProvider>
  )
}
