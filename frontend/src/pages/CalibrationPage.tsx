import { Check, RotateCcw, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { InfoHint } from '../components/ui/InfoHint'
import { ModuleBadge, PageHeader, StateMessage, buttonClass } from '../components/ui/PageHeader'
import { Section } from '../components/ui/Section'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { modules } from '../data/navigation'
import { useOpenFinding } from '../features/findings/FindingContext'
import { useQuery } from '../hooks/useQuery'
import { formatPercent } from '../lib/format'
import { useLive } from '../live/LiveProvider'
import type { Calibration, CalibrationItem, ModuleId, RouteId } from '../types'

function metrics(items: CalibrationItem[], t: number) {
  let tp = 0, fp = 0, fn = 0, tn = 0
  for (const i of items) {
    const pred = i.score >= t
    if (pred && i.label) tp++
    else if (pred) fp++
    else if (i.label) fn++
    else tn++
  }
  const precision = tp + fp ? tp / (tp + fp) : 1
  const recall = tp + fn ? tp / (tp + fn) : 0
  const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0
  return { tp, fp, fn, tn, precision, recall, f1 }
}

/** Precision / recall / F1 as a function of the threshold, with the current threshold marked. */
function CurveChart({ data, t }: { data: Calibration; t: number }) {
  const W = 600, H = 220, P = 32, L = 46
  const x = (v: number) => L + (v / 100) * (W - L - P)
  const y = (v: number) => H - P - v * (H - P * 2)
  const line = (k: 'precision' | 'recall' | 'f1') => data.curve.map((c, i) => `${i ? 'L' : 'M'}${x(c.t).toFixed(1)},${y(c[k]).toFixed(1)}`).join('')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Wykres precyzji, pełności i F1 w zależności od progu">
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <g key={v}>
          <line x1={L} x2={W - P} y1={y(v)} y2={y(v)} stroke="var(--color-line)" strokeDasharray={v ? '3 4' : undefined} />
          <text x={L - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--color-ink-subtle)">
            {v * 100}%
          </text>
        </g>
      ))}
      {[0, 25, 50, 75, 100].map((v) => (
        <text key={v} x={x(v)} y={H - 10} textAnchor="middle" fontSize="11" fill="var(--color-ink-subtle)">
          {v}
        </text>
      ))}
      <path d={line('recall')} fill="none" stroke="var(--color-risk-high)" strokeWidth="2.5" />
      <path d={line('precision')} fill="none" stroke="var(--color-navy-800)" strokeWidth="2.5" />
      <path d={line('f1')} fill="none" stroke="var(--color-ok)" strokeWidth="2" strokeDasharray="5 4" />
      <line x1={x(t)} x2={x(t)} y1={P - 8} y2={H - P} stroke="var(--color-ink)" strokeWidth="1.5" />
      <text x={x(t)} y={P - 12} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--color-ink)">
        próg {t}
      </text>
    </svg>
  )
}

/** Every labelled material placed on the score axis: red = real violation, blue = compliant. */
function ScoreStrip({ items, t, onOpen }: { items: CalibrationItem[]; t: number; onOpen: (id: number) => void }) {
  const rows: CalibrationItem[][] = []
  for (const it of [...items].sort((a, b) => a.score - b.score)) {
    const row = rows.find((r) => r.every((o) => Math.abs(o.score - it.score) > 3.2)) ?? (rows.push([]), rows[rows.length - 1])
    row.push(it)
  }
  return (
    <div>
      <div className="relative rounded-lg bg-surface-2" style={{ height: `${Math.max(3, rows.length) * 22 + 16}px` }}>
        <div className="absolute inset-y-0 bg-risk-critical/6" style={{ left: `${t}%`, right: 0 }} aria-hidden />
        <div className="absolute inset-y-0 w-0.5 bg-ink" style={{ left: `${t}%` }} aria-hidden />
        {rows.map((row, r) =>
          row.map((it) => (
            <button
              key={it.url}
              type="button"
              title={`${it.title} — ocena ${Math.round(it.score)} (${it.label ? 'naruszenie' : 'brak naruszenia'})`}
              onClick={() => it.finding_id && onOpen(it.finding_id)}
              className={`absolute size-3.5 -translate-x-1/2 rounded-full ring-2 ring-white transition-transform hover:scale-150 ${
                it.label ? 'bg-risk-critical' : 'border-2 border-navy-700 bg-white'
              }`}
              style={{ left: `${it.score}%`, top: `${8 + r * 22}px` }}
            />
          )),
        )}
      </div>
      <div className="mt-1 flex justify-between text-xs text-ink-subtle">
        <span>0 — niska ocena</span>
        <span>alert, jeśli ocena ≥ progu →</span>
        <span>100</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-ink-muted">
        <span className="flex items-center gap-2">
          <span className="size-3 rounded-full bg-risk-critical" /> materiał z rzeczywistym naruszeniem (etykieta)
        </span>
        <span className="flex items-center gap-2">
          <span className="size-3 rounded-full border-2 border-navy-700 bg-white" /> materiał zgodny (etykieta)
        </span>
      </div>
    </div>
  )
}

const OUTCOME = {
  tp: { label: 'Trafiony alert', className: 'text-ok' },
  tn: { label: 'Poprawnie pominięty', className: 'text-ink-muted' },
  fp: { label: 'Fałszywy alarm', className: 'text-risk-high-text' },
  fn: { label: 'Przeoczenie', className: 'text-risk-critical-text' },
}

export function CalibrationPage({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  const [module, setModule] = useState<ModuleId>('m2')
  const cal = useQuery(() => api.calibration(module), [module], ['findings', 'settings'])
  const [t, setT] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState<string | null>(null)
  const { bump } = useLive()
  const open = useOpenFinding()
  const data = cal.data

  useEffect(() => {
    if (data) setT(Math.round(data.threshold))
  }, [data?.threshold, module]) // eslint-disable-line react-hooks/exhaustive-deps

  const cur = t ?? 50
  const m = useMemo(() => metrics(data?.items ?? [], cur), [data, cur])
  const savedM = useMemo(() => metrics(data?.items ?? [], data?.threshold ?? 50), [data])
  const liveAlerts = (data?.scores_all ?? []).filter((s) => s >= cur).length
  const dirty = data && cur !== Math.round(data.threshold)

  const save = async (value: number) => {
    setSaving(true)
    try {
      await api.setThresholds({ [module]: value })
      setSaved(`Zapisano próg ${module.toUpperCase()} = ${value}. Wszystkie widoki i raporty używają nowej wartości.`)
      bump('settings', 'findings', 'activity')
    } finally {
      setSaving(false)
    }
  }

  const delta = (now: number, before: number) => {
    const d = Math.round((now - before) * 100)
    if (!d) return null
    return <span className={`ml-2 text-sm font-semibold ${d > 0 ? 'text-ok' : 'text-risk-critical-text'}`}>{d > 0 ? `+${d}` : d} pp</span>
  }

  return (
    <div className="animate-iw-fade">
      <PageHeader
        crumbs={[{ label: 'Strona główna', onClick: () => onNavigate('overview') }, { label: 'System' }, { label: 'Kalibracja' }]}
        title="Panel kalibracji"
        actions={
          <SegmentedControl
            ariaLabel="Moduł"
            value={module}
            onChange={(v) => {
              setModule(v)
              setSaved(null)
            }}
            options={(['m1', 'm2', 'm3'] as ModuleId[]).map((x) => ({ value: x, label: `${x.toUpperCase()} · ${modules[x].short}` }))}
          />
        }
        lead={
          <>
            Próg decyduje, od jakiej oceny materiał staje się alertem. <b className="font-semibold text-ink">Niższy próg</b> wykrywa więcej naruszeń
            (rośnie pełność), ale daje więcej fałszywych alarmów. <b className="font-semibold text-ink">Wyższy próg</b> — odwrotnie. Skutki zmiany
            liczymy na żywo na korpusie testowym z etykietami.
          </>
        }
      />

      {cal.error && !data && (
        <StateMessage title="Nie udało się wczytać danych kalibracji" tone="error">
          {cal.error}
        </StateMessage>
      )}
      {data && data.items.length === 0 && (
        <StateMessage title="Brak ocenionych materiałów z etykietami">
          Poczekaj na zakończenie pierwszego skanowania korpusu testowego (Źródła i scraper).
        </StateMessage>
      )}

      {data && data.items.length > 0 && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          <div className="flex xl:col-span-12">
            <Section title={`Próg alertu — moduł ${module.toUpperCase()}`} description={`Zapisany próg: ${data.threshold}. Rekomendowany (maks. F1, środek optymalnego zakresu): ${data.recommended ?? '—'}.`}>
              <div className="grid gap-8 px-5 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={cur}
                      onChange={(e) => {
                        setT(Number(e.target.value))
                        setSaved(null)
                      }}
                      aria-label="Próg alertu"
                      className="h-2 flex-1 cursor-pointer accent-navy-800"
                    />
                    <span className="w-16 rounded-lg border border-line-strong py-1.5 text-center text-2xl font-bold text-navy-900 tabular">{cur}</span>
                  </div>
                  <div className="mt-6">
                    <ScoreStrip items={data.items} t={cur} onOpen={open} />
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="rounded-lg border border-line p-4">
                    <p className="text-sm text-ink-muted">
                      Alerty przy tym progu <span className="text-xs">(wszystkie ocenione materiały)</span>
                    </p>
                    <p className="mt-1 text-3xl font-bold text-navy-900 tabular">{liveAlerts}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={!dirty || saving} onClick={() => save(cur)} className={buttonClass.primary}>
                      <Check size={16} /> Zastosuj próg {cur}
                    </button>
                    {data.recommended !== null && data.recommended !== cur && (
                      <button type="button" onClick={() => setT(data.recommended!)} className={buttonClass.secondary}>
                        <Sparkles size={16} /> Rekomendowany ({data.recommended})
                      </button>
                    )}
                    {dirty && (
                      <button type="button" onClick={() => setT(Math.round(data.threshold))} className={buttonClass.ghost}>
                        <RotateCcw size={15} /> Cofnij
                      </button>
                    )}
                  </div>
                  {saved && <p className="text-sm text-ok">{saved}</p>}
                </div>
              </div>
            </Section>
          </div>

          <div className="flex xl:col-span-5">
            <Section title="Jakość wykrywania" description={`Na ${data.items.length} materiałach z etykietą (${data.items.filter((i) => i.label).length} naruszeń).`}>
              <div className="grid grid-cols-3 gap-3 px-5 py-5 sm:px-6">
                {[
                  ['Precyzja', m.precision, savedM.precision, 'Jaka część alertów to rzeczywiste naruszenia. Spada, gdy rośnie liczba fałszywych alarmów.'],
                  ['Pełność', m.recall, savedM.recall, 'Jaka część rzeczywistych naruszeń została wykryta. Spada, gdy rośnie liczba przeoczeń.'],
                  ['F1', m.f1, savedM.f1, 'Średnia harmoniczna precyzji i pełności — jedna liczba do porównywania progów.'],
                ].map(([label, v, before, hint]) => (
                  <div key={label as string} className="rounded-lg bg-surface-2 p-3">
                    <p className="flex items-center gap-1 text-xs font-medium text-ink-muted">
                      {label} <InfoHint>{hint as string}</InfoHint>
                    </p>
                    <p className="mt-1 text-2xl font-bold text-navy-900 tabular">
                      {formatPercent(v as number)}
                    </p>
                    {dirty && delta(v as number, before as number)}
                  </div>
                ))}
              </div>
              <div className="px-5 pb-6 sm:px-6">
                <p className="mb-2 text-sm font-semibold text-ink">Macierz pomyłek</p>
                <div className="grid grid-cols-[auto_1fr_1fr] overflow-hidden rounded-lg border border-line text-sm">
                  <span />
                  <span className="border-b border-l border-line bg-surface-2 px-3 py-2 text-center text-xs font-semibold text-ink-muted">Alert</span>
                  <span className="border-b border-l border-line bg-surface-2 px-3 py-2 text-center text-xs font-semibold text-ink-muted">Brak alertu</span>
                  <span className="border-b border-line bg-surface-2 px-3 py-3 text-xs font-semibold text-ink-muted">Naruszenie</span>
                  <span className="border-b border-l border-line px-3 py-3 text-center">
                    <b className="text-xl text-ok tabular">{m.tp}</b>
                    <span className="block text-xs text-ink-muted">trafione</span>
                  </span>
                  <span className="border-b border-l border-line px-3 py-3 text-center">
                    <b className="text-xl text-risk-critical-text tabular">{m.fn}</b>
                    <span className="block text-xs text-ink-muted">przeoczone (FN)</span>
                  </span>
                  <span className="bg-surface-2 px-3 py-3 text-xs font-semibold text-ink-muted">Zgodny</span>
                  <span className="border-l border-line px-3 py-3 text-center">
                    <b className="text-xl text-risk-high-text tabular">{m.fp}</b>
                    <span className="block text-xs text-ink-muted">fałszywe alarmy (FP)</span>
                  </span>
                  <span className="border-l border-line px-3 py-3 text-center">
                    <b className="text-xl text-ink tabular">{m.tn}</b>
                    <span className="block text-xs text-ink-muted">poprawnie pominięte</span>
                  </span>
                </div>
              </div>
            </Section>
          </div>

          <div className="flex xl:col-span-7">
            <Section title="Precyzja i pełność a próg" description="Przesuń suwak — pionowa linia pokazuje wybrany próg.">
              <div className="px-5 py-5 sm:px-6">
                <CurveChart data={data} t={cur} />
                <div className="mt-2 flex flex-wrap gap-4 text-sm text-ink-muted">
                  <span className="flex items-center gap-2">
                    <span className="h-0.5 w-5 bg-navy-800" /> precyzja
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-0.5 w-5 bg-risk-high" /> pełność
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="h-0.5 w-5 border-t-2 border-dashed border-ok" /> F1
                  </span>
                </div>
              </div>
            </Section>
          </div>

          <div className="flex xl:col-span-12">
            <Section title="Materiały z etykietą" description="Wynik każdego materiału przy wybranym progu. Kliknij, aby zobaczyć uzasadnienie oceny.">
              <ul className="divide-y divide-line">
                {data.items.map((it) => {
                  const pred = it.score >= cur
                  const outcome = pred ? (it.label ? 'tp' : 'fp') : it.label ? 'fn' : 'tn'
                  return (
                    <li key={it.url}>
                      <button
                        type="button"
                        disabled={!it.finding_id}
                        onClick={() => it.finding_id && open(it.finding_id)}
                        className="grid w-full grid-cols-[48px_minmax(0,1fr)_auto] items-center gap-4 px-5 py-3 text-left hover:bg-navy-50/50 disabled:cursor-default sm:grid-cols-[48px_minmax(0,1fr)_150px_170px] sm:px-6"
                      >
                        <span className="text-lg font-bold text-navy-900 tabular">{Math.round(it.score)}</span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink">{it.note}</span>
                          <span className="block truncate text-xs text-ink-muted">{it.url}</span>
                        </span>
                        <span className="hidden text-sm sm:block">
                          {it.label ? <span className="text-risk-critical-text">naruszenie</span> : <span className="text-ink-muted">zgodny</span>}
                        </span>
                        <span className={`text-sm font-semibold ${OUTCOME[outcome].className}`}>{OUTCOME[outcome].label}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </Section>
          </div>
        </div>
      )}
      <p className="mt-8 text-sm text-ink-muted">
        <ModuleBadge module={module} /> Etykiety pochodzą z korpusu testowego (<code>demo-sites/generate.py</code>). Po podłączeniu próbek danych UKNF
        wystarczy dodać ich etykiety, aby kalibrować progi na rzeczywistych materiałach.
      </p>
    </div>
  )
}
