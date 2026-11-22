import { useState } from 'react'
import { api, type FindingFilters } from '../api/client'
import { PageHeader, StateMessage } from '../components/ui/PageHeader'
import { Section } from '../components/ui/Section'
import { FilterBar } from '../features/findings/FilterBar'
import { FindingsTable } from '../features/findings/FindingsTable'
import { useQuery } from '../hooks/useQuery'
import { plural } from '../lib/format'
import type { RouteId } from '../types'

export function AlertsPage({ onNavigate, initial }: { onNavigate: (id: RouteId) => void; initial: URLSearchParams }) {
  const [filters, setFilters] = useState<FindingFilters>({
    sort: 'score',
    level: initial.get('level') ?? undefined,
    module: initial.get('module') ?? undefined,
    status: initial.get('status') ?? undefined,
  })
  const key = JSON.stringify(filters)
  const res = useQuery(() => api.findings(filters), [key], ['findings', 'settings'])
  const total = res.data?.total ?? 0

  return (
    <div className="animate-iw-fade">
      <PageHeader
        crumbs={[{ label: 'Strona główna', onClick: () => onNavigate('overview') }, { label: 'Monitoring' }, { label: 'Rejestr alertów' }]}
        title="Rejestr alertów"
        lead="Wszystkie wyniki trzech modułów w jednym miejscu. Filtruj po dacie publikacji, źródle, poziomie ryzyka i module; otwórz wynik, aby zobaczyć dowody i zmienić status sprawy."
      />
      <FilterBar value={filters} onChange={setFilters} platforms={res.data?.platforms ?? []} />
      <div className="mt-6">
        {res.error && !res.data ? (
          <StateMessage title="Nie udało się wczytać alertów" tone="error">
            {res.error}
          </StateMessage>
        ) : (
          <Section
            title={`${total} ${plural(total, 'wynik', 'wyniki', 'wyników')}`}
            description={filters.include_below_threshold ? 'Pokazano także wyniki poniżej progu alertu.' : 'Wyniki z oceną równą lub wyższą od progu modułu.'}
          >
            <FindingsTable items={res.data?.items ?? []} />
          </Section>
        )}
      </div>
    </div>
  )
}
