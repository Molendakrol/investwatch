import { ExternalLink, FileLock2, X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../../api/client'
import { ModuleBadge } from '../../components/ui/PageHeader'
import { RiskBadge } from '../../components/ui/RiskBadge'
import { modules } from '../../data/navigation'
import { useQuery } from '../../hooks/useQuery'
import { formatDate, timeAgo } from '../../lib/format'
import { registerCategoryLabel, riskMeta, ruleStatusMeta } from '../../lib/risk'
import type { Finding, RuleResult } from '../../types'
import { StatusSelect } from './StatusSelect'

function Block({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="border-b border-line px-6 py-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-ink-subtle">{title}</h3>
        {aside}
      </div>
      {children}
    </section>
  )
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-0.5 break-words text-sm font-medium text-ink">{children}</dd>
    </div>
  )
}

function RuleRow({ r }: { r: RuleResult }) {
  const m = ruleStatusMeta[r.status]
  return (
    <li className="py-3">
      <div className="flex items-start gap-3">
        <span className={`mt-1.5 size-2 shrink-0 rounded-full ${m.dot}`} aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-xs font-semibold text-ink-subtle tabular">{r.id}.</span>
            <span className="font-semibold text-ink">{r.name}</span>
            <span className={`text-xs font-semibold ${m.className}`}>{m.label}</span>
          </p>
          <p className="mt-0.5 text-sm leading-relaxed text-ink-muted">{r.detail}</p>
          {r.status !== 'pass' &&
            r.evidence.map((e, i) => (
              <blockquote key={i} className="mt-2 rounded-r-md border-l-2 border-navy-600 bg-navy-50/60 px-3 py-1.5 text-sm text-ink">
                „{e}”
              </blockquote>
            ))}
          <p className="mt-1 text-xs text-ink-subtle">{r.legal_basis}</p>
        </div>
      </div>
    </li>
  )
}

function Rules({ rules }: { rules: RuleResult[] }) {
  const [showAll, setShowAll] = useState(false)
  const order = { fail: 0, warn: 1, pass: 2, na: 3 }
  const sorted = [...rules].sort((a, b) => order[a.status] - order[b.status])
  const relevant = sorted.filter((r) => r.status === 'fail' || r.status === 'warn')
  const rest = sorted.filter((r) => r.status === 'pass' || r.status === 'na')
  const counts = { fail: 0, warn: 0, pass: 0, na: 0 }
  rules.forEach((r) => (counts[r.status] += 1))
  return (
    <Block
      title="Kryteria informacji o ryzyku (18)"
      aside={
        <span className="text-xs text-ink-muted">
          <b className="text-risk-critical-text">{counts.fail}</b> naruszeń · <b className="text-risk-high-text">{counts.warn}</b> uwag ·{' '}
          <b className="text-ok">{counts.pass}</b> spełnionych · {counts.na} n/d
        </span>
      }
    >
      {relevant.length === 0 && <p className="text-sm text-ok">Wszystkie mające zastosowanie kryteria są spełnione.</p>}
      <ul className="divide-y divide-line">
        {relevant.map((r) => (
          <RuleRow key={r.id} r={r} />
        ))}
        {showAll && rest.map((r) => <RuleRow key={r.id} r={r} />)}
      </ul>
      {rest.length > 0 && (
        <button type="button" onClick={() => setShowAll((v) => !v)} className="mt-2 text-sm font-semibold text-navy-700 hover:underline">
          {showAll ? 'Ukryj spełnione i nie dotyczące' : `Pokaż pozostałe kryteria (${rest.length})`}
        </button>
      )}
    </Block>
  )
}

function Signals({ f }: { f: Finding }) {
  const signals = (f.signals ?? []).filter((s) => s.weight > 0)
  const notes = (f.signals ?? []).filter((s) => s.weight === 0)
  return (
    <Block title="Wykryte sygnały">
      <ul className="space-y-3">
        {signals.map((s) => (
          <li key={s.code} className="flex gap-3">
            <span className="mt-1 h-4 w-1.5 shrink-0 overflow-hidden rounded-full bg-navy-50" aria-hidden>
              <span className={`block w-full rounded-full ${riskMeta[f.level].bg}`} style={{ height: `${Math.min(100, s.weight * 160)}%` }} />
            </span>
            <span className="min-w-0">
              <span className="block font-semibold text-ink">{s.label}</span>
              {s.evidence && <span className="mt-0.5 block text-sm text-ink-muted">„{s.evidence}”</span>}
            </span>
          </li>
        ))}
      </ul>
      {notes.length > 0 && (
        <ul className="mt-4 space-y-1.5 border-t border-line pt-3">
          {notes.map((s) => (
            <li
              key={s.code}
              className={`text-sm ${s.code === 'register_missing' ? 'font-semibold text-risk-critical-text' : s.code.startsWith('register') ? 'font-semibold text-ok' : 'text-ink-muted'}`}
            >
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </Block>
  )
}

export function FindingDrawer({ id, onClose, onOpen }: { id: number; onClose: () => void; onOpen: (id: number) => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { data: f, error } = useQuery(() => api.finding(id), [id], ['findings'])
  const [fullText, setFullText] = useState(false)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [onClose])

  useEffect(() => setFullText(false), [id])

  return createPortal(
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="finding-title">
      <button type="button" aria-label="Zamknij szczegóły" className="animate-iw-fade absolute inset-0 bg-navy-950/40" onClick={onClose} />
      <aside className="animate-iw-slide-in absolute inset-y-0 right-0 flex w-full max-w-2xl flex-col bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div className="min-w-0">
            {f && (
              <div className="flex flex-wrap items-center gap-2">
                <ModuleBadge module={f.module} />
                <span className="text-sm font-medium text-ink-muted">{modules[f.module].short}</span>
                <RiskBadge level={f.level} />
                <span className="text-xs text-ink-subtle tabular">#{f.id}</span>
              </div>
            )}
            <h2 id="finding-title" className="mt-3 text-xl font-bold leading-snug text-ink">
              {f ? f.summary : error ? 'Nie udało się wczytać wyniku' : 'Wczytywanie…'}
            </h2>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Zamknij" className="-mr-2 rounded-md p-2 text-ink-muted hover:bg-surface hover:text-ink">
            <X size={22} strokeWidth={1.8} />
          </button>
        </header>

        {error && <p className="px-6 py-4 text-sm text-risk-critical-text">{error}</p>}
        {f && (
          <div className="flex-1 overflow-y-auto">
            <section className="border-b border-line bg-surface-2 px-6 py-5">
              <div className="flex flex-wrap gap-x-10 gap-y-5">
                <div>
                  <p className="text-xs text-ink-muted">Ocena ryzyka</p>
                  <p className="mt-1 flex items-baseline gap-1.5">
                    <span className={`text-5xl font-bold leading-none tabular ${riskMeta[f.level].text}`}>{Math.round(f.score)}</span>
                    <span className="text-sm text-ink-subtle">/ 100</span>
                  </p>
                  <p className="mt-1 text-xs text-ink-muted">{f.is_alert ? 'powyżej progu alertu' : 'poniżej progu alertu'}</p>
                </div>
                <dl className="grid flex-1 grid-cols-2 gap-x-6 gap-y-3">
                  <Meta label={f.module === 'm1' ? 'Podmiot reklamujący' : 'Podmiot'}>{f.entity ?? '—'}</Meta>
                  <Meta label="Firma z rejestru UKNF">
                    {f.firm ? (
                      <>
                        {f.firm}
                        {f.firm_category && <span className="block text-xs font-normal text-ink-muted">{registerCategoryLabel[f.firm_category] ?? f.firm_category}</span>}
                      </>
                    ) : f.module === 'm3' ? (
                      <span className="text-risk-critical-text">brak w rejestrze</span>
                    ) : (
                      '—'
                    )}
                  </Meta>
                  <Meta label="Źródło / platforma">{f.document.platform}</Meta>
                  <Meta label="Data publikacji">{formatDate(f.document.published_at, true)}</Meta>
                  <Meta label="Pierwsze wykrycie">{formatDate(f.document.first_seen, true)}</Meta>
                  <Meta label="Ostatnie skanowanie">
                    {timeAgo(f.document.last_seen)}
                    <span className="block text-xs font-normal text-ink-muted">
                      skanowań: {f.document.scan_count}, zmian treści: {f.document.change_count}
                    </span>
                  </Meta>
                </dl>
              </div>
              <div className="mt-4">
                <p className="mb-2 text-xs text-ink-muted">Status sprawy</p>
                <StatusSelect id={f.id} status={f.status} />
              </div>
            </section>

            <Block title="Lokalizacja materiału">
              <a
                href={f.document.url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="inline-flex max-w-full items-center gap-1.5 break-all text-sm font-semibold text-navy-700 hover:underline"
              >
                {f.document.url} <ExternalLink size={14} className="shrink-0" aria-hidden />
              </a>
              {f.document.has_raw && (
                <a
                  href={api.rawUrl(f.document.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 flex items-center gap-1.5 text-sm text-ink-muted hover:text-navy-800"
                >
                  <FileLock2 size={14} aria-hidden /> Zapisana kopia dowodowa · SHA-256 {f.document.content_hash?.slice(0, 12)}…
                </a>
              )}
              {f.document.duplicate_of && (
                <p className="mt-2 text-sm text-warn-text">Treść niemal identyczna z wcześniej wykrytym materiałem (dokument #{f.document.duplicate_of}).</p>
              )}
            </Block>

            {f.module === 'm2' && f.rules && <Rules rules={f.rules} />}
            {f.module !== 'm2' && <Signals f={f} />}

            <Block
              title="Treść materiału"
              aside={
                f.document.text && f.document.text.length > f.document.excerpt.length ? (
                  <button type="button" onClick={() => setFullText((v) => !v)} className="text-sm font-semibold text-navy-700 hover:underline">
                    {fullText ? 'Pokaż fragment' : 'Pokaż całość'}
                  </button>
                ) : undefined
              }
            >
              <p className="whitespace-pre-line rounded-lg bg-surface px-4 py-3 text-sm leading-relaxed text-ink">
                {fullText ? f.document.text : f.document.excerpt}
              </p>
            </Block>

            {f.related && f.related.length > 0 && (
              <Block title="Ten sam materiał w innych modułach">
                <ul className="space-y-2">
                  {f.related.map((r) => (
                    <li key={r.id}>
                      <button type="button" onClick={() => onOpen(r.id)} className="flex w-full items-center gap-3 rounded-lg border border-line px-3 py-2 text-left hover:border-navy-600">
                        <ModuleBadge module={r.module} />
                        <span className="flex-1 text-sm text-ink">{r.summary}</span>
                        <span className="text-sm font-semibold tabular">{Math.round(r.score)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Block>
            )}
          </div>
        )}
      </aside>
    </div>,
    document.body,
  )
}
