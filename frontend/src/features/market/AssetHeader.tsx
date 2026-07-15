import { Link } from 'react-router-dom'
import type { components } from '@/api/schema'

type AssetMetadata = components['schemas']['AssetMetadata']

interface AssetHeaderProps {
  asset: string
  metadata: AssetMetadata | null
}

export function AssetHeader({ asset, metadata }: AssetHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex items-center gap-2 text-xs text-text-secondary">
            <li>
              <Link to="/market" className="hover:text-text-primary">
                Market
              </Link>
            </li>
            <li className="text-text-disabled">/</li>
            <li className="text-text-emphasis">{metadata?.display_name ?? asset}</li>
          </ol>
        </nav>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold uppercase tracking-wide text-text-emphasis">
            {metadata?.display_name ?? asset.toUpperCase()}
          </h1>
          {metadata && (
            <span className="font-mono text-sm text-text-secondary">
              {metadata.ticker_continuous} · {metadata.exchange} · USD/{metadata.unit}
            </span>
          )}
          {/* Phase 2 RegimeBadge placeholder — nothing rendered in F4 */}
        </div>
      </div>
      <Link
        to={`/research?asset=${asset}`}
        className="py-1.5 flex items-center gap-2 rounded-md bg-accent px-3 text-sm font-medium text-bg-app hover:bg-accent-hover"
      >
        Open in Workbench →
      </Link>
    </div>
  )
}
