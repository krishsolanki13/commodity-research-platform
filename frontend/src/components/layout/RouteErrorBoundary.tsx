import { useRouteError, Link } from 'react-router-dom'

export function RouteErrorBoundary() {
  const error = useRouteError()
  const message = error instanceof Error ? error.message : 'Unknown error'
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
      <p className="text-sm font-medium text-text-primary">Something went wrong on this page.</p>
      <p className="font-mono text-xs text-text-secondary">{message}</p>
      <Link
        to="/research"
        className="rounded border border-border-default px-3 py-1.5 text-xs text-text-accent hover:bg-bg-hover"
      >
        Reload Research Workbench
      </Link>
    </div>
  )
}
