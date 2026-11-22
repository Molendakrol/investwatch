import { ChevronRight } from 'lucide-react'

export interface Crumb {
  label: string
  onClick?: () => void
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Ścieżka nawigacji" className="text-sm">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {items.map((c, i) => {
          const last = i === items.length - 1
          return (
            <li key={c.label} className="flex items-center gap-2">
              {c.onClick && !last ? (
                <button type="button" onClick={c.onClick} className="text-ink-muted hover:text-navy-800 hover:underline">
                  {c.label}
                </button>
              ) : (
                <span className={last ? 'font-semibold text-navy-800' : 'text-ink-muted'} aria-current={last ? 'page' : undefined}>
                  {c.label}
                </span>
              )}
              {!last && <ChevronRight size={14} className="text-ink-subtle" aria-hidden />}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
