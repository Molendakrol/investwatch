import { useEffect, useState, type ReactNode } from 'react'
import type { RouteId } from '../types'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

interface AppShellProps {
  route: RouteId
  onNavigate: (id: RouteId) => void
  children: ReactNode
}

export function AppShell({ route, onNavigate, children }: AppShellProps) {
  const [navOpen, setNavOpen] = useState(false)

  useEffect(() => {
    if (!navOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setNavOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navOpen])

  const go = (id: RouteId) => {
    setNavOpen(false)
    onNavigate(id)
  }

  return (
    <div className="min-h-dvh">
      <TopBar onOpenNav={() => setNavOpen(true)} onHome={() => go('overview')} />

      <div className="flex">
        {/* Desktop sidebar */}
        <aside className="sticky top-20 hidden h-[calc(100dvh-5rem)] shrink-0 lg:block">
          <Sidebar route={route} onNavigate={go} />
        </aside>

        <main className="min-w-0 flex-1">
          <div className="mx-auto max-w-[1400px] px-4 pb-16 pt-6 sm:px-6 lg:px-10 lg:pt-8">{children}</div>
        </main>
      </div>

      {/* Mobile drawer */}
      {navOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button
            type="button"
            aria-label="Zamknij menu"
            className="animate-iw-fade absolute inset-0 bg-navy-950/40"
            onClick={() => setNavOpen(false)}
          />
          <div className="animate-iw-slide-in relative h-full w-72 shadow-xl">
            <Sidebar route={route} onNavigate={go} onClose={() => setNavOpen(false)} />
          </div>
        </div>
      )}
    </div>
  )
}
