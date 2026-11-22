import { Pause, Play, Plus, RotateCcw, ScanLine, Search } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { PageHeader, buttonClass, inputClass } from '../components/ui/PageHeader'
import { Section } from '../components/ui/Section'
import { Tooltip } from '../components/ui/Tooltip'
import { useQuery } from '../hooks/useQuery'
import { formatNumber, hostOf, timeAgo } from '../lib/format'
import { registerCategoryLabel, sourceKindLabel } from '../lib/risk'
import { useLive } from '../live/LiveProvider'
import type { Job, RouteId, Source } from '../types'

const GROUP_LABEL: Record<Source['group'], string> = {
  register: 'Rejestr UKNF (dane referencyjne)',
  web: 'Źródła dodane przez analityków',
  social: 'Media społecznościowe',
  demo: 'Korpus testowy (materiały syntetyczne z etykietami)',
}

const JOB_STATUS: Record<Job['status'], { label: string; className: string }> = {
  queued: { label: 'W kolejce', className: 'bg-surface text-ink-muted ring-1 ring-inset ring-line' },
  running: { label: 'Pobieranie…', className: 'bg-navy-50 text-navy-800' },
  done: { label: 'Gotowe', className: 'bg-ok/10 text-ok' },
  failed: { label: 'Błąd', className: 'bg-risk-critical/10 text-risk-critical-text' },
}

function AddSource() {
  const [url, setUrl] = useState('')
  const [kind, setKind] = useState<Source['kind']>('html')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const { bump } = useLive()

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.addSource(url.trim(), kind)
      setMsg({ ok: true, text: r.job ? `Dodano i zakolejkowano skanowanie (zadanie #${r.job.id}).` : 'Źródło już istnieje — skanowanie jest w toku.' })
      setUrl('')
      bump('sources', 'jobs')
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 px-5 py-5 sm:px-6">
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px_auto]">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-muted">Adres URL</span>
          <input type="url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" className={inputClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-muted">Typ źródła</span>
          <select value={kind} onChange={(e) => setKind(e.target.value as Source['kind'])} className={inputClass}>
            {(['html', 'social', 'meta_ads', 'knf_register'] as const).map((k) => (
              <option key={k} value={k}>
                {sourceKindLabel[k]}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={busy || !url} className={`${buttonClass.primary} self-end`}>
          <Plus size={16} /> Dodaj i skanuj
        </button>
      </div>
      <p className="text-xs text-ink-muted">
        Scraper respektuje robots.txt, rotuje nagłówek User-Agent (i proxy, jeśli skonfigurowano <code>PROXIES</code>), ponawia próby z opóźnieniem
        wykładniczym i ogranicza częstotliwość zapytań do jednego hosta. Adresy sieci wewnętrznej są blokowane (ochrona przed SSRF).
      </p>
      {msg && <p className={`text-sm ${msg.ok ? 'text-ok' : 'text-risk-critical-text'}`}>{msg.text}</p>}
    </form>
  )
}

function SourceRow({ s }: { s: Source }) {
  const { bump } = useLive()
  const [busy, setBusy] = useState(false)
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
      bump('sources', 'jobs')
    } finally {
      setBusy(false)
    }
  }
  return (
    <tr className={s.active ? '' : 'opacity-55'}>
      <td className="py-3 pl-6 pr-3">
        <span className="block font-medium text-ink">{s.name.replace('Korpus testowy — ', '')}</span>
        <a href={s.url} target="_blank" rel="noopener noreferrer nofollow" className="block max-w-md truncate text-xs text-ink-muted hover:text-navy-700">
          {s.url}
        </a>
      </td>
      <td className="px-3 py-3 text-sm text-ink-muted">{sourceKindLabel[s.kind]}</td>
      <td className="px-3 py-3 text-sm">
        {s.last_status === 'failed' ? (
          <Tooltip content={s.last_error ?? 'Błąd'} align="start">
            <span tabIndex={0} className="cursor-help font-medium text-risk-critical-text">
              Błąd
            </span>
          </Tooltip>
        ) : s.last_status === 'done' ? (
          <span className="font-medium text-ok">OK</span>
        ) : (
          <span className="text-ink-subtle">jeszcze nie</span>
        )}
      </td>
      <td className="px-3 py-3 text-right text-sm text-ink tabular">{s.last_status ? s.items_found : '—'}</td>
      <td className="px-3 py-3 text-sm text-ink-muted">{timeAgo(s.last_run_at)}</td>
      <td className="py-3 pl-3 pr-6">
        <span className="flex justify-end gap-1">
          <button type="button" disabled={busy} onClick={() => act(() => api.runSource(s.id))} className={buttonClass.ghost} aria-label={`Skanuj teraz: ${s.name}`}>
            <ScanLine size={15} /> Skanuj
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => act(() => api.toggleSource(s.id, !s.active))}
            className={buttonClass.ghost}
            aria-label={s.active ? `Wstrzymaj: ${s.name}` : `Wznów: ${s.name}`}
          >
            {s.active ? <Pause size={15} /> : <Play size={15} />}
            {s.active ? 'Wstrzymaj' : 'Wznów'}
          </button>
        </span>
      </td>
    </tr>
  )
}

export function SourcesPage({ onNavigate }: { onNavigate: (id: RouteId) => void }) {
  const sources = useQuery(() => api.sources(), [], ['sources'])
  const jobs = useQuery(() => api.jobs(40), [], ['jobs'])
  const [q, setQ] = useState('')
  const register = useQuery(() => api.register(q || undefined), [q], ['register'])
  const { bump } = useLive()
  const [confirmReset, setConfirmReset] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  const groups = (['register', 'web', 'social', 'demo'] as const)
    .map((g) => ({ g, items: (sources.data ?? []).filter((s) => s.group === g) }))
    .filter((x) => x.items.length)

  const sweep = async () => {
    const r = await api.sweep()
    setNote(r.queued ? `Zakolejkowano ${r.queued} źródeł.` : 'Wszystkie źródła są już w kolejce.')
    bump('jobs', 'sources')
  }
  const reset = async () => {
    setConfirmReset(false)
    const r = await api.reset()
    setNote(`Wyczyszczono wyniki. Zakolejkowano ${r.queued} źródeł — alerty będą pojawiać się na żywo.`)
    bump('jobs', 'sources', 'findings', 'activity')
  }

  return (
    <div className="animate-iw-fade">
      <PageHeader
        crumbs={[{ label: 'Strona główna', onClick: () => onNavigate('overview') }, { label: 'System' }, { label: 'Źródła i scraper' }]}
        title="Źródła i scraper"
        lead="Silnik pobierający dane: kolejka zadań, harmonogram, kolektory stron WWW, postów z mediów społecznościowych, biblioteki reklam Meta oraz rejestru firm inwestycyjnych UKNF."
        actions={
          <>
            <button type="button" onClick={sweep} className={buttonClass.primary}>
              <ScanLine size={16} /> Skanuj wszystkie teraz
            </button>
            {confirmReset ? (
              <span className="flex items-center gap-2 rounded-lg border border-risk-critical/30 bg-risk-critical/5 px-3 py-1.5 text-sm">
                Usunąć wszystkie wyniki?
                <button type="button" onClick={reset} className="font-semibold text-risk-critical-text hover:underline">
                  Tak, wyczyść
                </button>
                <button type="button" onClick={() => setConfirmReset(false)} className="font-semibold text-ink-muted hover:underline">
                  Anuluj
                </button>
              </span>
            ) : (
              <button type="button" onClick={() => setConfirmReset(true)} className={buttonClass.secondary}>
                <RotateCcw size={16} /> Wyczyść wyniki i skanuj ponownie
              </button>
            )}
          </>
        }
      />
      {note && <p className="mb-4 rounded-lg border border-navy-100 bg-navy-50 px-4 py-3 text-sm text-navy-800">{note}</p>}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="flex xl:col-span-12">
          <Section title="Dodaj źródło" description="Strona WWW, eksport posta z platformy społecznościowej, odpowiedź Meta Ad Library API lub strona rejestru UKNF.">
            <AddSource />
          </Section>
        </div>

        <div className="flex xl:col-span-8">
          <Section title="Monitorowane źródła" description={`${sources.data?.length ?? 0} źródeł. Harmonogram skanuje aktywne źródła okresowo; rejestr UKNF raz na dobę.`}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-b border-line bg-surface-2 text-xs font-semibold uppercase tracking-wider text-ink-subtle">
                  <tr>
                    <th className="py-2.5 pl-6 pr-3">Źródło</th>
                    <th className="px-3 py-2.5">Typ</th>
                    <th className="px-3 py-2.5">Wynik</th>
                    <th className="px-3 py-2.5 text-right">Pozycje</th>
                    <th className="px-3 py-2.5">Ostatnio</th>
                    <th className="py-2.5 pl-3 pr-6" />
                  </tr>
                </thead>
                {groups.map(({ g, items }) => (
                  <tbody key={g} className="divide-y divide-line">
                    <tr>
                      <th colSpan={6} className="bg-white px-6 pb-1 pt-4 text-left text-xs font-semibold uppercase tracking-wider text-navy-800">
                        {GROUP_LABEL[g]}
                      </th>
                    </tr>
                    {items.map((s) => (
                      <SourceRow key={s.id} s={s} />
                    ))}
                  </tbody>
                ))}
              </table>
            </div>
          </Section>
        </div>

        <div className="flex xl:col-span-4">
          <Section title="Kolejka zadań" description="Na żywo. Worker pobiera zadania z kolejki (long-polling).">
            <ol className="divide-y divide-line">
              {(jobs.data ?? []).map((j) => (
                <li key={j.id} className="px-5 py-3 sm:px-6">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold ${JOB_STATUS[j.status].className}`}>{JOB_STATUS[j.status].label}</span>
                    <span className="text-xs text-ink-subtle tabular">#{j.id}</span>
                    <span className="ml-auto text-xs text-ink-subtle">
                      {j.duration_ms !== null ? `${(j.duration_ms / 1000).toFixed(1).replace('.', ',')} s` : timeAgo(j.created_at)}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm text-ink" title={j.url}>
                    {hostOf(j.url)}
                    <span className="text-ink-muted">{j.url.replace(/^https?:\/\/[^/]+/, '').slice(0, 60)}</span>
                  </p>
                  <p className="text-xs text-ink-muted">
                    {sourceKindLabel[j.kind]} · {j.trigger === 'schedule' ? 'harmonogram' : 'ręcznie'}
                    {j.status === 'done' && ` · ${j.result_count} poz.`}
                    {j.attempts > 1 && ` · próba ${j.attempts}`}
                  </p>
                  {j.error && <p className="mt-1 text-xs text-risk-critical-text">{j.error}</p>}
                </li>
              ))}
            </ol>
          </Section>
        </div>

        <div className="flex xl:col-span-12">
          <Section
            title="Rejestr firm inwestycyjnych UKNF"
            description={
              register.data
                ? `${formatNumber(register.data.summary.total)} podmiotów pobranych z knf.gov.pl ${register.data.summary.fetched_at ? `(${timeAgo(register.data.summary.fetched_at)})` : ''}. Służy do rozpoznawania firm (M1, M2) i weryfikacji uprawnień (M3).`
                : 'Wczytywanie…'
            }
          >
            <div className="px-5 py-5 sm:px-6">
              <div className="flex flex-wrap gap-2">
                {Object.entries(register.data?.summary.by_category ?? {}).map(([c, n]) => (
                  <span key={c} className="rounded-full bg-surface px-3 py-1 text-sm text-ink ring-1 ring-inset ring-line">
                    {registerCategoryLabel[c] ?? c}: <b className="tabular">{formatNumber(n)}</b>
                  </span>
                ))}
              </div>
              <label className="relative mt-4 block max-w-md">
                <span className="sr-only">Szukaj w rejestrze</span>
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" aria-hidden />
                <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Szukaj firmy w rejestrze…" className={`${inputClass} pl-9`} />
              </label>
              <ul className="mt-4 grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
                {(register.data?.items ?? []).slice(0, 30).map((r) => (
                  <li key={r.id} className="border-b border-line py-2.5">
                    <span className="block text-sm font-medium text-ink">{r.name}</span>
                    <span className="block text-xs text-ink-muted">
                      {registerCategoryLabel[r.category] ?? r.category}
                      {r.license_date && ` · zezwolenie ${r.license_date}`}
                      {r.scope && ` · zakres: ${r.scope.slice(0, 40)}`}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}
