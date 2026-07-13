import { WifiOff } from 'lucide-react'
import { Button } from '@/ui/button'

interface ApiUnreachableProps {
  onRetry: () => void
}

export function ApiUnreachable({ onRetry }: ApiUnreachableProps) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-6 bg-bg-app">
      <WifiOff size={64} strokeWidth={1.5} className="text-text-secondary" />
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-xl font-semibold text-text-emphasis">
          Cannot reach the API
        </p>
        <p className="text-sm text-text-secondary">
          Make sure the backend is running:{' '}
          <code className="font-mono text-text-primary">make dev</code>
        </p>
      </div>
      <Button variant="primary" onClick={onRetry}>
        Retry
      </Button>
    </div>
  )
}
