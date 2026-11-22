import type { ReactNode } from 'react'

interface SectionProps {
  id?: string
  title: string
  description?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}

/** White card with a clear heading — the base block of every dashboard section. */
export function Section({ id, title, description, actions, children, className = '', bodyClassName = '' }: SectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={id ? `${id}-title` : undefined}
      className={`flex min-w-0 flex-1 scroll-mt-24 flex-col overflow-hidden rounded-xl border border-line bg-white ${className}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b border-line px-5 py-4 sm:px-6">
        <div className="min-w-0">
          <h2 id={id ? `${id}-title` : undefined} className="text-lg font-semibold text-ink">
            {title}
          </h2>
          {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </header>
      <div className={`flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  )
}
