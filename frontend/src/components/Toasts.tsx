import { BellRing, X } from 'lucide-react'
import { createPortal } from 'react-dom'
import { modules } from '../data/navigation'
import { useOpenFinding } from '../features/findings/FindingContext'
import { riskMeta } from '../lib/risk'
import { useLive } from '../live/LiveProvider'

/** Real-time notifications for newly detected high / critical alerts (WebSocket). */
export function Toasts() {
  const { toasts, dismissToast } = useLive()
  const open = useOpenFinding()
  if (!toasts.length) return null
  return createPortal(
    <div className="pointer-events-none fixed right-4 top-24 z-40 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-3" aria-live="polite">
      {toasts.map(({ key, finding: f }) => (
        <div key={key} className="animate-iw-slide-in pointer-events-auto overflow-hidden rounded-xl border border-line bg-white shadow-xl">
          <div className={`h-1 ${riskMeta[f.level].bg}`} />
          <div className="flex items-start gap-3 p-4">
            <BellRing size={18} className={`mt-0.5 shrink-0 ${riskMeta[f.level].text}`} aria-hidden />
            <button
              type="button"
              onClick={() => {
                open(f.id)
                dismissToast(key)
              }}
              className="min-w-0 flex-1 text-left"
            >
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-subtle">
                Nowy alert · {f.module.toUpperCase()} {modules[f.module].short} · ocena {Math.round(f.score)}
              </p>
              <p className="mt-1 text-sm font-semibold leading-snug text-ink">{f.summary}</p>
              <p className="mt-1 truncate text-xs text-ink-muted">{f.document.url}</p>
            </button>
            <button type="button" onClick={() => dismissToast(key)} aria-label="Zamknij powiadomienie" className="rounded p-1 text-ink-subtle hover:text-ink">
              <X size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>,
    document.body,
  )
}
