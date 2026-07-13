import * as React from 'react'
import { cn } from '@/lib/cn'

interface PanelProps {
  title?: string
  actions?: React.ReactNode
  children: React.ReactNode
  padding?: boolean
  className?: string
}

export function Panel({ title, actions, children, padding = true, className }: PanelProps) {
  return (
    <div className={cn('rounded-md border border-border-default bg-bg-panel', className)}>
      {title !== undefined && (
        <div className="flex items-center justify-between border-b border-border-default px-4 py-2">
          <span className="text-sm font-semibold text-text-emphasis">{title}</span>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={cn(padding && 'p-4')}>{children}</div>
    </div>
  )
}
