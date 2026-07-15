import { useMemo } from 'react'
import { useAssetOhlcv } from '@/api/hooks/useAssetOhlcv'
import { ReturnHistogram } from '@/components/charts/ReturnHistogram'

interface AssetDistributionPanelProps {
  asset: string
  fromDate: string
  toDate: string
}

export function AssetDistributionPanel({ asset, fromDate, toDate }: AssetDistributionPanelProps) {
  const { data: ohlcv, isLoading } = useAssetOhlcv(asset, {
    from_date: fromDate,
    to_date: toDate,
    downsample: 'view',
  })

  const logReturns = useMemo(() => {
    const closes = ohlcv?.data.columns.close ?? []
    const returns: number[] = []
    for (let i = 1; i < closes.length; i++) {
      const prev = closes[i - 1]
      const curr = closes[i]
      if (prev !== null && curr !== null && prev > 0) {
        returns.push(Math.log(curr / prev))
      }
    }
    return returns
  }, [ohlcv])

  return (
    <ReturnHistogram
      values={logReturns}
      markers={['mean', 'median']}
      height={250}
      title="Return Distribution"
      loading={isLoading}
    />
  )
}
