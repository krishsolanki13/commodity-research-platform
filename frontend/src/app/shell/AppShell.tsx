import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useWorkspace } from '@/stores/workspace'
import { SidebarNav } from '@/app/shell/SidebarNav'
import { TopBar } from '@/app/shell/TopBar'
import { ContextBar } from '@/app/shell/ContextBar'
import { CommandPalette } from '@/app/shell/CommandPalette'
import { ComparisonTray } from '@/app/shell/ComparisonTray'

export function AppShell() {
  const { theme, density, toggleNavCollapsed } = useWorkspace()
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.dataset.density = density
  }, [theme, density])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      if (e.key === '[') {
        toggleNavCollapsed()
        return
      }

      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(true)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [toggleNavCollapsed])

  return (
    <div className="flex h-screen flex-col bg-bg-app">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-4 focus:py-2 focus:text-sm focus:text-bg-app"
      >
        Skip to main content
      </a>

      <TopBar onOpenPalette={() => setPaletteOpen(true)} />

      <div className="flex flex-1 overflow-hidden">
        <SidebarNav />

        <div className="flex flex-1 flex-col overflow-hidden">
          <ContextBar />
          <main
            id="main-content"
            role="main"
            className="flex-1 overflow-y-auto"
          >
            <Outlet />
          </main>
        </div>
      </div>

      <ComparisonTray />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}
