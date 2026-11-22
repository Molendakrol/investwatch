import { Download, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { api, type FindingFilters } from '../api/client'
import { ModuleBadge, PageHeader, StateMessage, buttonClass } from '../components/ui/PageHeader'
import { Section } from '../components/ui/Section'
import { modules } from '../data/navigation'
import { FilterBar } from '../features/findings/FilterBar'
import { FindingsTable } from '../features/findings/FindingsTable'
import { AdhocCheck } from '../features/m2/AdhocCheck'
import { useQuery } from '../hooks/useQuery'
import { clockTime, formatNumber, plural, timeAgo } from '../lib/format'
import type { ModuleId, RouteId } from '../types'

const RESULT_TITLE: Record<ModuleId, string> = {
  m1: 'Raport: reklamy firm inwestycyjnych u podmiotów trzecich',
  m2: 'Materiały niespełniające kryteriów informacji o ryzyku',
  m3: 'Raport: potencjalne doradztwo bez zezwolenia',
}

const RESULT_DESC: Record<ModuleId, string> = {
  m1: 'Dane firmy inwestycyjnej, podmiotu reklamującego, treść reklamy i dokładny URL. Każdy wpis jest aktualizowany przy kolejnym skanowaniu.',
  m2: 'Flagowane automatycznie, gdy ocena łączna przekroczy próg. Otwórz materiał, aby zobaczyć wynik każdego z 18 kryteriów.',
  m3: 'Dane podmiotu, treść oferty, lokalizacja i status w rejestrze UKNF.',
}

export function ModulePage({ module, onNavigate }: { module: ModuleId; onNavigate: (id: RouteId) => void }) {
  const [filters, setFilters] = useState<FindingFilters>({ sort: 'score' })
  const key = JSON.stringify(filters)
  const res = useQuery(() => api.findings({ ...filters, module }), [key, module], ['findings', 'settings'])
  const settings = useQuery(() => api.settings(), [], ['settings'])
  const stats = useQuery(() => api.stats(90), [], ['jobs'])
  const meta = modules[module]
  const total = res.data?.total ?? 0

  return (
    <div className="animate-iw-fade">
      <PageHeader
        crumbs={[{ label: 'Strona główna', onClick: () => onNavigate('overview') }, { label: 'Moduły analityczne' }, { label: meta.short }]}
        title={meta.title}
        badge={<ModuleBadge module={module} />}
        lead={meta.summary}
        actions={
          <a href={api.reportUrl(module)} className={buttonClass.secondary} download>
            <Download size={16} /> Eksportuj raport CSV
          </a>
        }
      />

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-line bg-white px-5 py-4">
          <p className="text-sm text-ink-muted">Wyniki powyżej progu</p>
          <p className="mt-1 text-[2rem] font-bold leading-none text-navy-900 tabular">{res.data ? formatNumber(total) : '—'}</p>
        </div>
        <div className="rounded-xl border border-line bg-white px-5 py-4">
          <p className="text-sm text-ink-muted">Próg alertu</p>
          <p className="mt-1 text-[2rem] font-bold leading-none text-navy-900 tabular">{settings.data?.thresholds[module] ?? '—'}</p>
          <button type="button" onClick={() => onNavigate('calibration')} className="mt-1 text-sm font-semibold text-navy-700 hover:underline">
            Zmień w Kalibracji →
          </button>
        </div>
        <div className="rounded-xl border border-line bg-white px-5 py-4">
          <p className="flex items-center gap-1.5 text-sm text-ink-muted">
            <RefreshCw size={14} aria-hidden /> Okresowa aktualizacja
          </p>
          <p className="mt-1 font-semibold text-ink">co {settings.data?.sweep_interval_minutes ?? '—'} min</p>
          <p className="text-sm text-ink-muted">
            ostatnio {clockTime(stats.data?.last_sweep)} ({timeAgo(stats.data?.last_sweep)})
          </p>
        </div>
      </div>

      {module === 'm2' && (
        <div className="mb-6">
          <AdhocCheck />
        </div>
      )}

      <FilterBar value={filters} onChange={setFilters} platforms={res.data?.platforms ?? []} showModule={false} />
      <div className="mt-6">
        {res.error && !res.data ? (
          <StateMessage title="Nie udało się wczytać wyników" tone="error">
            {res.error}
          </StateMessage>
        ) : (
          <Section title={RESULT_TITLE[module]} description={`${total} ${plural(total, 'pozycja', 'pozycje', 'pozycji')} · ${RESULT_DESC[module]}`}>
            <FindingsTable items={res.data?.items ?? []} variant={module} />
          </Section>
        )}
      </div>
    </div>
  )
}
