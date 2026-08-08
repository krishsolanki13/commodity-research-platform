/**
 * ValidationSummaryTable — IS vs OOS metrics from ValidationReportResponse.
 *
 * Schema field names (flat):
 *   insample_sharpe / outsample_sharpe
 *   insample_return / outsample_return
 *   overfitting_ratio, psr, dsr (report-level singles)
 *
 * Max drawdown and n_trades are fold-level only — aggregated here from folds.
 * Win rate is not present in ValidationReportResponse — omitted.
 */
import type { components } from '@/api/schema'
import { dec, pct } from '@/lib/fmt'

type ValidationReportResponse = components['schemas']['ValidationReportResponse']
type WalkForwardFoldResponse = components['schemas']['WalkForwardFoldResponse']

interface ValidationSummaryTableProps {
  report: ValidationReportResponse
}

type RowValues = {
  isVal: number | null
  oosVal: number | null
}

type RowDef = {
  label: string
  format: (v: number) => string
  higherIsBetter: boolean
  isDrawdown?: boolean
  get: (report: ValidationReportResponse, folds: WalkForwardFoldResponse[]) => RowValues
}

function meanNullable(vals: Array<number | null | undefined>): number | null {
  const nums = vals.filter((v): v is number => v != null && Number.isFinite(v))
  if (nums.length === 0) return null
  return nums.reduce((a, b) => a + b, 0) / nums.length
}

function sumNumber(vals: number[]): number | null {
  if (vals.length === 0) return null
  return vals.reduce((a, b) => a + b, 0)
}

const ROWS: RowDef[] = [
  {
    label: 'Sharpe',
    format: (v) => dec(v, 2),
    higherIsBetter: true,
    get: (r) => ({ isVal: r.insample_sharpe, oosVal: r.outsample_sharpe }),
  },
  {
    label: 'Total Return',
    format: (v) => pct(v, 1),
    higherIsBetter: true,
    get: (r) => ({ isVal: r.insample_return, oosVal: r.outsample_return }),
  },
  {
    label: 'Max Drawdown',
    format: (v) => pct(v, 1),
    higherIsBetter: false,
    isDrawdown: true,
    get: (_r, folds) => ({
      isVal: meanNullable(folds.map((f) => f.train_max_dd)),
      oosVal: meanNullable(folds.map((f) => f.test_max_dd)),
    }),
  },
  {
    label: 'N Trades',
    format: (v) => v.toFixed(0),
    higherIsBetter: true,
    get: (_r, folds) => ({
      isVal: sumNumber(folds.map((f) => f.train_n_trades)),
      oosVal: sumNumber(folds.map((f) => f.test_n_trades)),
    }),
  },
  {
    label: 'Overfitting Ratio',
    format: (v) => dec(v, 2),
    higherIsBetter: false,
    get: (r) => ({ isVal: null, oosVal: r.overfitting_ratio }),
  },
  {
    label: 'PSR',
    format: (v) => dec(v, 3),
    higherIsBetter: true,
    get: (r) => ({ isVal: null, oosVal: r.psr }),
  },
  {
    label: 'DSR',
    format: (v) => dec(v, 3),
    higherIsBetter: true,
    get: (r) => ({ isVal: null, oosVal: r.dsr }),
  },
]

function oosColorClass(
  isVal: number | null,
  oosVal: number | null,
  _higherIsBetter: boolean,
  isDrawdown: boolean,
): string {
  if (
    isVal === null ||
    oosVal === null ||
    Number.isNaN(isVal) ||
    Number.isNaN(oosVal) ||
    isVal === 0
  ) {
    return 'text-text-secondary'
  }
  if (isDrawdown) {
    // Smaller absolute drawdown is better
    return Math.abs(oosVal) <= Math.abs(isVal) ? 'text-gain' : 'text-loss'
  }
  const ratio = oosVal / isVal
  if (ratio >= 0.8) return 'text-gain'
  if (ratio >= 0.5) return 'text-warn'
  return 'text-loss'
}

function isPresentNumber(v: number | null | undefined): v is number {
  return v !== null && v !== undefined && Number.isFinite(v)
}

/** Format a cell; treat null/NaN/non-finite and formatters that yield "NaN" as em dash. */
function formatCell(
  format: (v: number) => string,
  v: number | null | undefined,
): string {
  if (!isPresentNumber(v)) return '—'
  const formatted = format(v)
  return formatted === 'NaN' ? '—' : formatted
}

export function ValidationSummaryTable({ report }: ValidationSummaryTableProps) {
  const folds = report.folds ?? []

  return (
    <div className="overflow-hidden rounded border border-border-default">
      <table className="w-full table-fixed border-collapse text-sm">
        <thead className="bg-bg-raised">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
              Metric
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary">
              In-Sample
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary">
              Out-of-Sample
            </th>
            <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-text-secondary">
              OOS/IS
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-default">
          {ROWS.map((row) => {
            const { isVal, oosVal } = row.get(report, folds)
            const ratio =
              isPresentNumber(isVal) &&
              isPresentNumber(oosVal) &&
              isVal !== 0
                ? oosVal / isVal
                : null
            const oosClass = oosColorClass(
              isPresentNumber(isVal) ? isVal : null,
              isPresentNumber(oosVal) ? oosVal : null,
              row.higherIsBetter,
              row.isDrawdown ?? false,
            )

            return (
              <tr key={row.label} className="hover:bg-bg-hover">
                <td className="px-3 py-2 font-medium text-text-secondary">{row.label}</td>
                <td className="px-3 py-2 text-right font-mono text-text-primary">
                  {formatCell(row.format, isVal)}
                </td>
                <td className={`px-3 py-2 text-right font-mono ${oosClass}`}>
                  {formatCell(row.format, oosVal)}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-secondary">
                  {ratio !== null && Number.isFinite(ratio) ? dec(ratio, 2) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
