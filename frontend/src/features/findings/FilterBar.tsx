import { Search, X } from 'lucide-react'
import type { FindingFilters } from '../../api/client'
import { inputClass } from '../../components/ui/PageHeader'
import { RISK_LEVELS, STATUSES, riskMeta, statusMeta } from '../../lib/risk'

interface FilterBarProps {
  value: FindingFilters
  onChange: (next: FindingFilters) => void
  platforms: string[]
  showModule?: boolean
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <label className="flex min-w-0 flex-col gap-1">
      <span className="text-xs font-medium text-ink-muted">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
        <option value="">Wszystkie</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  )
}

/** Filters required by the brief: date, source, risk level and analytical module (+ status, search). */
export function FilterBar({ value, onChange, platforms, showModule = true }: FilterBarProps) {
  const set = (patch: Partial<FindingFilters>) => onChange({ ...value, ...patch })
  const active = Object.entries(value).some(([k, v]) => v && !['sort', 'include_below_threshold'].includes(k))
  return (
    <div className="rounded-xl border border-line bg-white p-4 sm:p-5">
      <div className={`grid grid-cols-1 gap-3 sm:grid-cols-2 ${showModule ? 'lg:grid-cols-6' : 'lg:grid-cols-5'}`}>
        <label className="flex min-w-0 flex-col gap-1 sm:col-span-2">
          <span className="text-xs font-medium text-ink-muted">Szukaj</span>
          <span className="relative">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle" aria-hidden />
            <input
              type="search"
              value={value.q ?? ''}
              onChange={(e) => set({ q: e.target.value })}
              placeholder="Podmiot, firma, URL, fragment treści…"
              className={`${inputClass} pl-9`}
            />
          </span>
        </label>
        {showModule && (
          <Select
            label="Moduł"
            value={value.module ?? ''}
            onChange={(v) => set({ module: v })}
            options={[
              ['m1', 'M1 · Ekosystem zewnętrzny'],
              ['m2', 'M2 · Informacja o ryzyku'],
              ['m3', 'M3 · Doradztwo bez zezwolenia'],
            ]}
          />
        )}
        <Select label="Poziom ryzyka" value={value.level ?? ''} onChange={(v) => set({ level: v })} options={RISK_LEVELS.map((l) => [l, riskMeta[l].label])} />
        <Select label="Status" value={value.status ?? ''} onChange={(v) => set({ status: v })} options={STATUSES.map((s) => [s, statusMeta[s].label])} />
        <Select label="Źródło" value={value.platform ?? ''} onChange={(v) => set({ platform: v })} options={platforms.map((p) => [p, p])} />
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-muted">Opublikowano od</span>
          <input type="date" value={value.date_from ?? ''} onChange={(e) => set({ date_from: e.target.value })} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-muted">do</span>
          <input type="date" value={value.date_to ?? ''} onChange={(e) => set({ date_to: e.target.value })} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-ink-muted">Sortuj</span>
          <select value={value.sort ?? 'score'} onChange={(e) => set({ sort: e.target.value as 'score' | 'date' })} className={inputClass}>
            <option value="score">Najwyższa ocena</option>
            <option value="date">Najnowsze publikacje</option>
          </select>
        </label>
        <label className="mb-2 flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={!!value.include_below_threshold}
            onChange={(e) => set({ include_below_threshold: e.target.checked })}
            className="size-4 accent-navy-800"
          />
          Pokaż także wyniki poniżej progu
        </label>
        {active && (
          <button type="button" onClick={() => onChange({ sort: value.sort })} className="mb-1 ml-auto inline-flex items-center gap-1 text-sm font-semibold text-navy-700 hover:underline">
            <X size={14} /> Wyczyść filtry
          </button>
        )}
      </div>
    </div>
  )
}
