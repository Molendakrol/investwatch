import { useMemo, useState } from 'react'
import { formatNumber } from '../../lib/format'
import { RISK_LEVELS, riskMeta } from '../../lib/risk'
import type { RiskLevel, Stats } from '../../types'

const STACK: RiskLevel[] = ['critical', 'high', 'medium', 'low']
const sum = (c: Record<RiskLevel, number>) => c.critical + c.high + c.medium + c.low

function niceCeil(max: number) {
  if (max <= 4) return 4
  const magnitude = 10 ** Math.floor(Math.log10(max))
  const step = magnitude / 2
  return Math.ceil(max / step) * step
}

/** Stacked bar chart: alerts per day by risk level (publication date, fallback: detection date). */
export function TimelineChart({ points, focus }: { points: Stats['timeline']; focus: RiskLevel | null }) {
  const [hovered, setHovered] = useState<number | null>(null)
  const yMax = useMemo(() => niceCeil(Math.max(0, ...points.map((p) => sum(p.counts)))), [points])
  const every = Math.ceil(points.length / 8)
  const label = (iso: string) => new Date(iso).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' })
  const hp = hovered !== null ? points[hovered] : null
  const gap = points.length <= 10 ? 'gap-2 sm:gap-4' : 'gap-[2px] sm:gap-1'

  return (
    <div>
      <div className="relative" onMouseLeave={() => setHovered(null)}>
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between" aria-hidden>
          {[1, 0.5, 0].map((t) => (
            <div key={t} className={`relative border-t ${t === 0 ? 'border-line-strong' : 'border-dashed border-line'}`}>
              <span className="absolute -top-2.5 right-0 bg-white pl-2 text-xs text-ink-subtle tabular">{formatNumber(Math.round(yMax * t))}</span>
            </div>
          ))}
        </div>
        <div className={`relative flex h-56 items-end pr-8 ${gap}`} role="img" aria-label="Wykres liczby alertów w czasie według poziomu ryzyka">
          {points.map((p, i) => {
            const t = sum(p.counts)
            return (
              <div key={p.date} className="flex h-full flex-1 cursor-pointer flex-col justify-end" onMouseEnter={() => setHovered(i)}>
                <div
                  className={`flex min-h-0 flex-col-reverse overflow-hidden rounded-t-[3px] transition-opacity ${hovered !== null && hovered !== i ? 'opacity-50' : ''}`}
                  style={{ height: `${(t / yMax) * 100}%` }}
                >
                  {STACK.map((lvl) => (
                    <div
                      key={lvl}
                      style={{ height: t ? `${(p.counts[lvl] / t) * 100}%` : 0, background: riskMeta[lvl].fill, opacity: focus && focus !== lvl ? 0.15 : 1 }}
                      className="w-full transition-opacity"
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
        {hp && (
          <div
            className="pointer-events-none absolute top-0 z-10 min-w-40 rounded-lg border border-line bg-white px-3.5 py-3 shadow-lg"
            style={hovered! < points.length / 2 ? { left: `${((hovered! + 1) / points.length) * 90}%` } : { right: `${((points.length - hovered!) / points.length) * 90 + 6}%` }}
          >
            <p className="text-xs font-medium text-ink-muted">{label(hp.date)}</p>
            <p className="text-base font-semibold text-ink tabular">{sum(hp.counts)} alertów</p>
            <ul className="mt-2 space-y-1">
              {RISK_LEVELS.map((l) => (
                <li key={l} className="flex items-center justify-between gap-4 text-xs text-ink-muted">
                  <span className="flex items-center gap-1.5">
                    <span className={`size-2 rounded-full ${riskMeta[l].bg}`} aria-hidden />
                    {riskMeta[l].label}
                  </span>
                  <span className="font-semibold text-ink tabular">{hp.counts[l]}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className={`mt-2 flex pr-8 ${gap}`} aria-hidden>
        {points.map((p, i) => (
          <span key={p.date} className="flex-1 overflow-visible whitespace-nowrap text-xs text-ink-subtle">
            {i % every === 0 ? label(p.date) : ''}
          </span>
        ))}
      </div>
    </div>
  )
}
