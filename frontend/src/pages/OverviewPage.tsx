import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import { TimelineChart } from '../components/charts/TimelineChart'
import { InfoHint } from '../components/ui/InfoHint'
import { ModuleBadge, PageHeader, StateMessage } from '../components/ui/PageHeader'
import { Section } from '../components/ui/Section'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { modules } from '../data/navigation'
import { LinkCheck } from '../features/check/LinkCheck'
import { FindingsTable } from '../features/findings/FindingsTable'
import { useQuery } from '../hooks/useQuery'
import { clockTime, formatNumber, plural, timeAgo } from '../lib/format'
import { RISK_LEVELS, riskMeta } from '../lib/risk'
import type { ModuleId, RiskLevel, RouteId } from '../types'

const PERIODS = [
  { value: '7', label: '7 dni' },
  { value: '30', label: '30 dni' },
  { value: '90', label: '90 dni' },
]

const ACTIVITY_LABEL = { sweep: 'Skanowanie', flag: 'Alert', system: 'System', analyst: 'Analityk' } as const
const ACTIVITY_CLASS = {
  sweep: 'bg-surface text-ink-muted ring-1 ring-inset ring-line',
  flag: 'bg-risk-critical/10 text-risk-critical-text',
  system: 'bg-warn-bg text-warn-text',
  analyst: 'bg-navy-50 text-navy-800',
} as const

export function OverviewPage({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  const [days, setDays] = useState('30')
  const [focus, setFocus] = useState<RiskLevel | null>(null)
  const stats = useQuery(() => api.stats(Number(days)), [days], ['findings', 'jobs', 'settings', 'register'])
  const latest = useQuery(() => api.findings({ sort: 'date' }), [], ['findings', 'settings'])
  const activity = useQuery(() => api.activity(12), [], ['activity'])
  const s = stats.data

  if (stats.error && !s) {
    return (
      <>
        <PageHeader crumbs={[{ label: 'Strona główna' }, { label: 'Przegląd' }]} title="Przegląd" />
        <StateMessage title="Nie można połączyć się z API" tone="error">
          {stats.error} Uruchom stos poleceniem <code>docker compose up</code> lub <code>scripts/dev.sh</code>.
        </StateMessage>
      </>
    )
  }

  const k = s?.kpi
  const topModule = k ? (Object.entries(k.by_module) as [ModuleId, number][]).sort((a, b) => b[1] - a[1])[0] : null

  return (
    <div className="animate-iw-fade">
      <PageHeader
        crumbs={[{ label: 'Strona główna' }, { label: 'Przegląd' }]}
        title="Przegląd"
        actions={
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-ink-muted">Okres:</span>
            <SegmentedControl ariaLabel="Okres analizy" options={PERIODS} value={days} onChange={setDays} />
          </div>
        }
        lead={
          k ? (
            k.alerts > 0 ? (
              <p className="text-xl text-ink">
                W ciągu ostatnich {days} dni wykryto{' '}
                <strong className="font-semibold text-navy-800">
                  {formatNumber(k.alerts)} {plural(k.alerts, 'alert', 'alerty', 'alertów')}
                </strong>
                , w tym <strong className="font-semibold text-risk-critical-text">{k.critical} krytycznych</strong>.
                {topModule && topModule[1] > 0 && (
                  <> Najwięcej w module {topModule[0].toUpperCase()} — {modules[topModule[0]].short.toLowerCase()}.</>
                )}
              </p>
            ) : (
              <p>Brak alertów powyżej progu w wybranym okresie.</p>
            )
          ) : (
            <p>Wczytywanie danych…</p>
          )
        }
      />

      <p className="-mt-2 mb-6 max-w-4xl text-base leading-relaxed text-ink-muted">
        InvestWatch pobiera treści z sieci i mediów społecznościowych, porównuje je z rejestrem firm inwestycyjnych UKNF i ocenia w trzech
        modułach: reklamy u podmiotów trzecich (M1), informacja o ryzyku w materiałach firm (M2) i doradztwo bez zezwolenia (M3).
      </p>

      <div className="mb-6">
        <LinkCheck />
      </div>

      {/* status strip */}
      <dl className="grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-white lg:grid-cols-5">
        {[
          ['Ostatnie skanowanie', s?.last_sweep ? `${clockTime(s.last_sweep)} (${timeAgo(s.last_sweep)})` : '—'],
          ['Kolejka zadań', k ? (k.queue ? `${k.queue} w toku` : 'pusta') : '—'],
          ['Źródła aktywne', s ? `${s.sources.active} z ${s.sources.total}${s.sources.failed ? ` · ${s.sources.failed} z błędem` : ''}` : '—'],
          ['Rejestr UKNF', s ? `${formatNumber(s.register.total)} podmiotów` : '—'],
          ['Progi M1 / M2 / M3', s ? `${s.thresholds.m1} / ${s.thresholds.m2} / ${s.thresholds.m3}` : '—'],
        ].map(([label, value], i) => (
          <div key={label} className={`border-line px-5 py-4 ${i % 2 === 0 ? 'border-r' : ''} ${i < 4 ? 'border-b lg:border-b-0' : ''} lg:border-r lg:last:border-r-0`}>
            <dt className="text-sm text-ink-muted">{label}</dt>
            <dd className="mt-1 font-semibold text-ink tabular">{value}</dd>
          </div>
        ))}
      </dl>

      {k && k.queue > 0 && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-navy-100 bg-navy-50 px-4 py-3 text-sm text-navy-800">
          <span className="size-2 animate-iw-pulse rounded-full bg-navy-700" aria-hidden />
          Trwa skanowanie źródeł — wyniki pojawiają się na bieżąco.
          <button type="button" onClick={() => onNavigate('sources')} className="ml-auto font-semibold hover:underline">
            Podgląd kolejki →
          </button>
        </div>
      )}

      {/* KPIs */}
      <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Przeanalizowane materiały', k?.documents, 'Strony, posty i reklamy pobrane przez scraper i ocenione przez silnik analizy.'],
          ['Alerty powyżej progu', k?.alerts, 'Wyniki z oceną równą lub wyższą od progu modułu (ustawianego w Kalibracji).'],
          ['Ryzyko krytyczne', k?.critical, 'Alerty z oceną ≥ 85 — wiele poważnych sygnałów naraz.'],
          ['Otwarte sprawy', k?.open, 'Alerty o statusie Nowy, W weryfikacji lub Eskalowany.'],
        ].map(([label, value, hint]) => (
          <div key={label as string} className="rounded-xl border border-line bg-white px-5 py-5">
            <dt className="flex items-center gap-1.5 text-sm font-medium text-ink-muted">
              {label}
              <InfoHint>{hint}</InfoHint>
            </dt>
            <dd className="mt-3 text-[2rem] font-bold leading-none tracking-tight text-navy-900 tabular">
              {value === undefined ? '—' : formatNumber(value as number)}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="flex xl:col-span-8">
          <Section title="Alerty w czasie" description="Według daty publikacji materiału (gdy brak — daty wykrycia). Kliknij poziom, aby go wyróżnić.">
            <div className="px-5 py-5 sm:px-6">
              {s && <TimelineChart points={s.timeline} focus={focus} />}
              <div className="mt-4 flex flex-wrap gap-2">
                {RISK_LEVELS.map((l) => (
                  <button
                    key={l}
                    type="button"
                    aria-pressed={focus === l}
                    onClick={() => setFocus(focus === l ? null : l)}
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm transition-colors ${
                      focus === l ? 'border-navy-600 bg-navy-50 font-semibold text-navy-800' : 'border-line text-ink-muted hover:border-navy-600'
                    }`}
                  >
                    <span className={`size-2.5 rounded-full ${riskMeta[l].bg}`} aria-hidden />
                    {riskMeta[l].label}
                    <span className="font-semibold text-ink tabular">{k?.by_level[l] ?? 0}</span>
                  </button>
                ))}
              </div>
            </div>
          </Section>
        </div>

        <div className="flex xl:col-span-4">
          <Section title="Moduły analityczne" description="Alerty powyżej progu w wybranym okresie.">
            <ul className="divide-y divide-line">
              {(['m1', 'm2', 'm3'] as ModuleId[]).map((m) => (
                <li key={m}>
                  <button type="button" onClick={() => onNavigate(m)} className="group flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-navy-50/50 sm:px-6">
                    <ModuleBadge module={m} />
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold text-ink group-hover:text-navy-800">{modules[m].short}</span>
                      <span className="mt-0.5 block text-sm leading-snug text-ink-muted">{modules[m].question}</span>
                    </span>
                    <span className="text-2xl font-bold text-navy-900 tabular">{k?.by_module[m] ?? '—'}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Section>
        </div>

        <div className="flex xl:col-span-8">
          <Section
            title="Najnowsze alerty"
            description="Kliknij, aby zobaczyć dowody, uzasadnienie i zmienić status."
            actions={
              <button type="button" onClick={() => onNavigate('alerts')} className="inline-flex items-center gap-1 text-sm font-semibold text-navy-700 hover:underline">
                Rejestr alertów <ArrowRight size={15} />
              </button>
            }
          >
            <FindingsTable items={(latest.data?.items ?? []).slice(0, 6)} empty="Brak alertów — trwa skanowanie lub progi są wysokie." />
          </Section>
        </div>

        <div className="flex xl:col-span-4">
          <Section title="Aktywność systemu" description="Na żywo: skanowania, alerty, działania analityków.">
            <ol className="divide-y divide-line">
              {(activity.data ?? []).slice(0, 8).map((a) => (
                <li key={a.id} className="grid grid-cols-[48px_minmax(0,1fr)] gap-3 px-5 py-3 sm:px-6">
                  <span className="pt-0.5 text-sm font-semibold text-ink-muted tabular">{clockTime(a.ts)}</span>
                  <span>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold ${ACTIVITY_CLASS[a.kind]}`}>{ACTIVITY_LABEL[a.kind]}</span>
                    <span className="mt-1 block text-sm leading-relaxed text-ink">{a.message}</span>
                  </span>
                </li>
              ))}
            </ol>
          </Section>
        </div>

        <div className="flex xl:col-span-6">
          <Section title="Najczęściej naruszane kryteria (M2)" description="Na podstawie art. 44 rozporządzenia del. 2017/565.">
            <RankList
              items={(s?.top_rules ?? []).map((r) => ({ key: r.id, label: `${r.id}. ${r.name}`, sub: r.legal_basis, count: r.count }))}
              onClick={() => onNavigate('m2')}
            />
          </Section>
        </div>
        <div className="flex xl:col-span-6">
          <Section title="Najczęstsze sygnały (M1 i M3)" description="Co najczęściej uruchamia alerty o reklamach i doradztwie.">
            <RankList
              items={(s?.top_signals ?? []).map((x) => ({ key: `${x.module}${x.code}`, label: x.label, sub: x.module === 'm1' ? 'M1 · ekosystem zewnętrzny' : 'M3 · doradztwo', count: x.count }))}
            />
          </Section>
        </div>
      </div>
    </div>
  )
}

function RankList({ items, onClick }: { items: { key: string; label: string; sub: string; count: number }[]; onClick?: () => void }) {
  if (!items.length) return <p className="px-6 py-10 text-center text-sm text-ink-muted">Brak danych w wybranym okresie.</p>
  const max = Math.max(...items.map((i) => i.count))
  return (
    <ol className="space-y-4 px-5 py-5 sm:px-6">
      {items.map((it, i) => (
        <li key={it.key}>
          <button type="button" onClick={onClick} disabled={!onClick} className="w-full text-left disabled:cursor-default">
            <span className="flex items-baseline justify-between gap-3">
              <span className="min-w-0">
                <span className="text-[0.9375rem] text-ink">{it.label}</span>
                <span className="block text-xs text-ink-subtle">{it.sub}</span>
              </span>
              <span className="font-semibold text-ink tabular">{it.count}</span>
            </span>
            <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-navy-50">
              <span className={`block h-full rounded-full ${i === 0 ? 'bg-navy-800' : 'bg-navy-600/45'}`} style={{ width: `${(it.count / max) * 100}%` }} />
            </span>
          </button>
        </li>
      ))}
    </ol>
  )
}
