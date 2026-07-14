import * as React from 'react'
import { cn } from '@/lib/cn'

interface KbdProps {
  children: React.ReactNode
  className?: string
}

export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        'inline-flex items-center rounded-sm border border-border-strong',
        'px-1.5 py-0.5 bg-bg-raised font-mono text-xs text-text-secondary',
        className
      )}
    >
      {children}
    </kbd>
  )
}
