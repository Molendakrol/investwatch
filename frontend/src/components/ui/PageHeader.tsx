import type { ReactNode } from 'react'
import { Breadcrumbs, type Crumb } from './Breadcrumbs'

interface PageHeaderProps {
  crumbs: Crumb[]
  title: string
  badge?: ReactNode
  lead?: ReactNode
  actions?: ReactNode
}

export function PageHeader({ crumbs, title, badge, lead, actions }: PageHeaderProps) {
  return (
    <div className="mb-6">
      <Breadcrumbs items={crumbs} />
      <div className="mt-5 flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[2.25rem] font-bold leading-tight tracking-tight text-ink sm:text-[2.5rem]">{title}</h1>
          {badge}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      {lead && <div className="mt-3 max-w-4xl text-lg leading-relaxed text-ink-muted">{lead}</div>}
    </div>
  )
}

export function ModuleBadge({ module }: { module: 'm1' | 'm2' | 'm3' }) {
  return (
    <span className="inline-flex rounded-md bg-navy-800 px-2 py-0.5 text-xs font-bold tracking-wide text-white">
      {module.toUpperCase()}
    </span>
  )
}

export function StateMessage({ title, children, tone = 'neutral' }: { title: string; children?: ReactNode; tone?: 'neutral' | 'error' }) {
  return (
    <div
      className={`rounded-xl border px-6 py-10 text-center ${tone === 'error' ? 'border-risk-critical/30 bg-risk-critical/5' : 'border-line bg-white'}`}
    >
      <p className={`font-semibold ${tone === 'error' ? 'text-risk-critical-text' : 'text-ink'}`}>{title}</p>
      {children && <div className="mx-auto mt-1 max-w-xl text-sm text-ink-muted">{children}</div>}
    </div>
  )
}

export const buttonClass = {
  primary:
    'inline-flex items-center gap-2 rounded-lg bg-navy-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-navy-900 disabled:cursor-not-allowed disabled:opacity-50',
  secondary:
    'inline-flex items-center gap-2 rounded-lg border border-line-strong bg-white px-4 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-navy-600 hover:text-navy-800 disabled:cursor-not-allowed disabled:opacity-50',
  ghost: 'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-semibold text-navy-700 hover:bg-navy-50',
}

export const inputClass =
  'w-full rounded-lg border border-line-strong bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:border-navy-600 focus:outline-none focus:ring-2 focus:ring-navy-100'
