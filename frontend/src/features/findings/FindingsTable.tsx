import { ChevronRight } from 'lucide-react'
import { ModuleBadge } from '../../components/ui/PageHeader'
import { RiskBadge } from '../../components/ui/RiskBadge'
import { formatDate, hostOf } from '../../lib/format'
import { registerCategoryLabel, riskMeta } from '../../lib/risk'
import type { Finding } from '../../types'
import { useOpenFinding } from './FindingContext'
import { StatusPill } from './StatusSelect'

type Variant = 'all' | 'm1' | 'm2' | 'm3'

const HEADERS: Record<Variant, string[]> = {
  all: ['Ocena', 'Materiał i źródło', 'Publikacja', 'Status'],
  m1: ['Ocena', 'Firma inwestycyjna', 'Podmiot reklamujący i treść', 'Lokalizacja', 'Status'],
  m2: ['Ocena', 'Firma i materiał', 'Naruszone kryteria', 'Publikacja', 'Status'],
  m3: ['Ocena', 'Podmiot i oferta', 'Rejestr UKNF', 'Lokalizacja', 'Status'],
}

function Score({ f }: { f: Finding }) {
  return (
    <span className="flex flex-col">
      <span className={`text-2xl font-bold leading-none tabular ${riskMeta[f.level].text}`}>{Math.round(f.score)}</span>
      <span className="mt-1 h-1 w-10 overflow-hidden rounded-full bg-navy-50" aria-hidden>
        <span className={`block h-full ${riskMeta[f.level].bg}`} style={{ width: `${f.score}%` }} />
      </span>
    </span>
  )
}

function Chips({ items, tone = 'neutral' }: { items: string[]; tone?: 'neutral' | 'danger' }) {
  return (
    <span className="mt-2 flex flex-wrap gap-1.5">
      {items.slice(0, 3).map((s) => s.split(':')[0].split(' (')[0]).map((s) => (
        <span
          key={s}
          className={`rounded-md px-2 py-0.5 text-xs ${tone === 'danger' ? 'bg-risk-critical/8 text-risk-critical-text' : 'bg-surface text-ink-muted ring-1 ring-inset ring-line'}`}
        >
          {s}
        </span>
      ))}
    </span>
  )
}

function Cells({ f, variant }: { f: Finding; variant: Variant }) {
  const d = f.document
  const where = (
    <span className="text-sm">
      <span className="block font-medium text-ink">{d.platform}</span>
      <span className="block truncate text-ink-muted" title={d.url}>
        {hostOf(d.url)}
      </span>
      <span className="block text-xs text-ink-subtle">{formatDate(d.published_at || d.first_seen)}</span>
    </span>
  )
  switch (variant) {
    case 'm1':
      return (
        <>
          <span className="text-sm">
            <span className="block font-semibold text-ink">{f.firm}</span>
            <span className="text-xs text-ink-muted">{registerCategoryLabel[f.firm_category ?? ''] ?? f.firm_category}</span>
          </span>
          <span className="min-w-0 text-sm">
            <span className="block font-semibold text-ink group-hover:text-navy-800">{f.entity}</span>
            <span className="mt-0.5 line-clamp-2 text-ink-muted">{d.excerpt}</span>
            <Chips items={f.top_signals} />
          </span>
          {where}
        </>
      )
    case 'm2':
      return (
        <>
          <span className="min-w-0 text-sm">
            <span className="block font-semibold text-ink group-hover:text-navy-800">{f.entity ?? hostOf(d.url)}</span>
            <span className="mt-0.5 line-clamp-1 text-ink-muted">{d.title || d.url}</span>
          </span>
          <span className="min-w-0">
            <Chips items={f.top_signals} tone="danger" />
          </span>
          <span className="text-sm text-ink-muted">{formatDate(d.published_at || d.first_seen)}</span>
        </>
      )
    case 'm3':
      return (
        <>
          <span className="min-w-0 text-sm">
            <span className="block font-semibold text-ink group-hover:text-navy-800">{f.entity}</span>
            <span className="mt-0.5 line-clamp-2 text-ink-muted">{d.excerpt}</span>
          </span>
          <span className="text-sm">
            {f.firm ? (
              <span className="font-semibold text-ok">w rejestrze</span>
            ) : (
              <span className="font-semibold text-risk-critical-text">brak w rejestrze</span>
            )}
          </span>
          {where}
        </>
      )
    default:
      return (
        <>
          <span className="min-w-0 text-sm">
            <span className="flex flex-wrap items-center gap-2">
              <ModuleBadge module={f.module} />
              <RiskBadge level={f.level} />
            </span>
            <span className="mt-1.5 block font-semibold leading-snug text-ink group-hover:text-navy-800">{f.summary}</span>
            <span className="mt-0.5 block truncate text-ink-muted" title={d.url}>
              {d.platform} · {hostOf(d.url)}
            </span>
            <Chips items={f.top_signals} />
          </span>
          <span className="text-sm text-ink-muted">{formatDate(d.published_at || d.first_seen)}</span>
        </>
      )
  }
}

const GRID: Record<Variant, string> = {
  all: 'md:grid-cols-[56px_minmax(0,1fr)_100px_110px_20px]',
  m1: 'md:grid-cols-[56px_190px_minmax(0,1fr)_160px_110px_20px]',
  m2: 'md:grid-cols-[56px_minmax(0,1fr)_minmax(0,1.1fr)_100px_110px_20px]',
  m3: 'md:grid-cols-[56px_minmax(0,1fr)_120px_160px_110px_20px]',
}

export function FindingsTable({ items, variant = 'all', empty }: { items: Finding[]; variant?: Variant; empty?: string }) {
  const open = useOpenFinding()
  if (!items.length) {
    return <p className="px-6 py-12 text-center text-sm text-ink-muted">{empty ?? 'Brak wyników dla wybranych filtrów.'}</p>
  }
  return (
    <div>
      <div className={`hidden gap-4 border-b border-line bg-surface-2 px-6 py-2.5 text-xs font-semibold uppercase tracking-wider text-ink-subtle md:grid ${GRID[variant]}`}>
        {HEADERS[variant].map((h) => (
          <span key={h}>{h}</span>
        ))}
        <span />
      </div>
      <ul className="divide-y divide-line">
        {items.map((f) => (
          <li key={f.id}>
            <button type="button" onClick={() => open(f.id)} className="group block w-full px-5 py-4 text-left transition-colors hover:bg-navy-50/50 sm:px-6">
              {/* desktop row */}
              <span className={`hidden items-start gap-4 md:grid ${GRID[variant]}`}>
                <Score f={f} />
                <Cells f={f} variant={variant} />
                <span>
                  <StatusPill status={f.status} />
                </span>
                <ChevronRight size={18} className="mt-1 text-ink-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-navy-800" aria-hidden />
              </span>
              {/* mobile card */}
              <span className="flex gap-4 md:hidden">
                <Score f={f} />
                <span className="flex min-w-0 flex-1 flex-col gap-2">
                  <span className="flex flex-wrap items-center gap-2">
                    <ModuleBadge module={f.module} />
                    <RiskBadge level={f.level} />
                    <StatusPill status={f.status} />
                  </span>
                  <span className="font-semibold leading-snug text-ink">{f.summary}</span>
                  <span className="truncate text-xs text-ink-muted">
                    {f.document.platform} · {hostOf(f.document.url)} · {formatDate(f.document.published_at || f.document.first_seen)}
                  </span>
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
