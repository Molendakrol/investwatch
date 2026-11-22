import { riskMeta } from '../../lib/risk'
import type { RiskLevel } from '../../types'

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${riskMeta[level].tint} ${riskMeta[level].text}`}>
      <span aria-hidden className={`inline-block size-1.5 shrink-0 rounded-full ${riskMeta[level].bg}`} />
      {riskMeta[level].label}
    </span>
  )
}
