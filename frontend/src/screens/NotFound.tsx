import { useNavigate } from 'react-router-dom'
import { Button } from '@/ui/button'

export default function NotFoundScreen() {
  const navigate = useNavigate()
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
      <span className="font-mono text-6xl text-text-secondary">404</span>
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-xl font-semibold text-text-emphasis">
          Page not found
        </h1>
        <p className="text-sm text-text-secondary">
          The page you're looking for doesn't exist or was removed.
        </p>
      </div>
      <div className="flex gap-3">
        <Button variant="primary" onClick={() => void navigate('/market')}>
          Go to Market Overview
        </Button>
        <Button variant="outline" onClick={() => void navigate('/runs')}>
          Run Explorer
        </Button>
      </div>
    </div>
  )
}
