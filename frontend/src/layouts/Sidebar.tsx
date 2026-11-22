import {
  ChartNoAxesCombined,
  DatabaseZap,
  ListChecks,
  Megaphone,
  ShieldAlert,
  SlidersHorizontal,
  UserRoundSearch,
  X,
  type LucideIcon,
} from 'lucide-react'
import { api } from '../api/client'
import { navGroups } from '../data/navigation'
import { useQuery } from '../hooks/useQuery'
import { clockTime, formatNumber } from '../lib/format'
import { useLive } from '../live/LiveProvider'
import type { NavItem, RouteId } from '../types'

const icons: Record<RouteId, LucideIcon> = {
  overview: ChartNoAxesCombined,
  alerts: ListChecks,
  m1: Megaphone,
  m2: ShieldAlert,
  m3: UserRoundSearch,
  sources: DatabaseZap,
  calibration: SlidersHorizontal,
}

interface SidebarProps {
  route: RouteId
  onNavigate: (id: RouteId) => void
  onClose?: () => void
  counts?: Partial<Record<RouteId, number>>
}

function NavLink({ item, active, count, onNavigate }: { item: NavItem; active: boolean; count?: number; onNavigate: (id: RouteId) => void }) {
  const Icon = icons[item.id]
  return (
    <li>
      <a
        href={`#/${item.id}`}
        onClick={(e) => {
          e.preventDefault()
          onNavigate(item.id)
        }}
        aria-current={active ? 'page' : undefined}
        title={item.description}
        className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-[0.9375rem] transition-colors ${
          active ? 'bg-navy-50 font-semibold text-navy-800' : 'text-ink hover:bg-surface hover:text-navy-800'
        }`}
      >
        <Icon size={18} strokeWidth={1.75} className={`shrink-0 ${active ? 'text-navy-800' : 'text-ink-subtle group-hover:text-navy-700'}`} />
        <span className="flex-1 leading-snug">
          {item.badge && <span className="mr-1.5 text-xs font-semibold text-ink-subtle">{item.badge}</span>}
          {item.label}
        </span>
        {count !== undefined && count > 0 && (
          <span className="rounded-full bg-navy-800 px-2 py-0.5 text-[0.6875rem] font-semibold text-white tabular">{count}</span>
        )}
      </a>
    </li>
  )
}

export function Sidebar({ route, onNavigate, onClose }: SidebarProps) {
  const { status } = useLive()
  const stats = useQuery(() => api.stats(30), [], ['findings', 'jobs', 'settings'])
  const k = stats.data?.kpi
  const counts: Partial<Record<RouteId, number>> = k
    ? { alerts: k.open, m1: k.by_module.m1, m2: k.by_module.m2, m3: k.by_module.m3 }
    : {}

  return (
    <nav aria-label="Menu główne" className="flex h-full w-72 flex-col border-r border-line bg-white">
      {onClose && (
        <div className="flex h-16 items-center justify-between border-b border-line px-5 lg:hidden">
          <span className="text-base font-semibold text-navy-800">Menu</span>
          <button type="button" onClick={onClose} aria-label="Zamknij menu" className="rounded-md p-2 text-ink-muted hover:bg-surface hover:text-ink">
            <X size={20} strokeWidth={1.8} />
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-7">
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-ink-subtle">{group.label}</p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink key={item.id} item={item} active={route === item.id} count={counts[item.id]} onNavigate={onNavigate} />
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="m-4 space-y-2 rounded-lg border border-line bg-surface-2 px-4 py-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-ink">
          <span
            className={`size-2 rounded-full ${status === 'open' ? 'animate-iw-pulse bg-ok' : status === 'connecting' ? 'bg-risk-medium' : 'bg-risk-critical'}`}
            aria-hidden
          />
          {status === 'open' ? 'Połączenie na żywo' : status === 'connecting' ? 'Łączenie…' : 'Brak połączenia'}
        </p>
        <p className="text-xs leading-relaxed text-ink-muted">
          Ostatnie skanowanie: {clockTime(stats.data?.last_sweep)}
          {k && k.queue > 0 && <> · w kolejce: {k.queue}</>}
          <br />
          Rejestr UKNF: {stats.data ? formatNumber(stats.data.register.total) : '—'} podmiotów
        </p>
      </div>
    </nav>
  )
}
