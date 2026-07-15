/**
 * Sparkline — compact SVG line chart for use inside DataGrid cells.
 *
 * PURE SVG — zero ECharts. ECharts instances inside grid cells would be
 * too expensive. SVG renders dozens of sparklines instantly as static markup.
 *
 * Null policy: null values create gaps. Each contiguous non-null segment is
 * rendered as a separate <polyline> element.
 *
 * Color: via CSS custom properties through currentColor — no hex literals.
 */
import { cn } from '@/lib/cn'

interface SparklineProps {
  values: (number | null)[]
  tone?: 'gain' | 'loss' | 'neutral' | 'auto'
  width?: number
  height?: number
  className?: string
}

export function Sparkline({
  values,
  tone = 'auto',
  width = 80,
  height = 24,
  className,
}: SparklineProps) {
  const nonNullValues = values.filter((v): v is number => v !== null)

  if (nonNullValues.length < 2) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        className={className}
        aria-hidden="true"
      />
    )
  }

  const min = Math.min(...nonNullValues)
  const max = Math.max(...nonNullValues)
  const range = max - min || 1
  const padding = 1

  // SVG coordinate system: y=0 is TOP. Invert so high values go up.
  const toY = (v: number) => height - padding - ((v - min) / range) * (height - padding * 2)
  const toX = (i: number) => (i / (values.length - 1)) * width

  // Determine stroke color via CSS custom property
  const firstNonNull = nonNullValues[0]
  const lastNonNull = nonNullValues[nonNullValues.length - 1]

  let colorVar: string
  if (tone === 'gain') {
    colorVar = 'var(--gain-500)'
  } else if (tone === 'loss') {
    colorVar = 'var(--loss-500)'
  } else if (tone === 'neutral') {
    colorVar = 'var(--text-secondary)'
  } else {
    // auto: derive from trend
    colorVar =
      lastNonNull > firstNonNull
        ? 'var(--gain-500)'
        : lastNonNull < firstNonNull
          ? 'var(--loss-500)'
          : 'var(--text-secondary)'
  }

  // Split values into contiguous non-null segments
  // Each segment becomes a separate <polyline> (the null gap policy)
  const segments: Array<Array<{ x: number; y: number }>> = []
  let currentSegment: Array<{ x: number; y: number }> = []

  values.forEach((v, i) => {
    if (v === null) {
      if (currentSegment.length > 0) {
        segments.push(currentSegment)
        currentSegment = []
      }
    } else {
      currentSegment.push({ x: toX(i), y: toY(v) })
    }
  })
  if (currentSegment.length > 0) segments.push(currentSegment)

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={cn('overflow-visible', className)}
      style={{ color: colorVar }}
      aria-hidden="true"
    >
      {segments.map((segment, segIdx) => (
        <polyline
          key={segIdx}
          points={segment.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}
    </svg>
  )
}
