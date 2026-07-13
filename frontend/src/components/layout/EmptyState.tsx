import { InboxIcon } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from '@/ui/button'

interface EmptyStateAction {
  label: string
  onClick?: () => void
  href?: string
}

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  body: string
  action?: EmptyStateAction
  className?: string
}

export function EmptyState({
  icon: Icon = InboxIcon,
  title,
  body,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 p-8',
        className
      )}
    >
      <Icon size={48} strokeWidth={1.5} className="text-text-secondary" />
      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-lg font-semibold text-text-emphasis">{title}</p>
        <p className="max-w-xs text-sm text-text-secondary">{body}</p>
      </div>
      {action && (
        action.href ? (
          <a
            href={action.href}
            className="text-sm font-medium text-text-accent underline-offset-4 hover:underline"
          >
            {action.label}
          </a>
        ) : (
          <Button variant="primary" onClick={action.onClick}>
            {action.label}
          </Button>
        )
      )}
    </div>
  )
}
