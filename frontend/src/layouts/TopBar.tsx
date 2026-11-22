import { Menu, Radio } from 'lucide-react'
import { Logo } from '../components/Logo'
import { Tooltip } from '../components/ui/Tooltip'
import { useTextSize } from '../hooks/useTextSize'
import { useLive } from '../live/LiveProvider'

interface TopBarProps {
  onOpenNav: () => void
  onHome: () => void
}

export function TopBar({ onOpenNav, onHome }: TopBarProps) {
  const text = useTextSize()
  const { status } = useLive()

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white">
      <div className="flex h-20 items-center gap-4 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenNav}
          aria-label="Otwórz menu"
          className="-ml-1 rounded-md p-2 text-navy-800 hover:bg-navy-50 lg:hidden"
        >
          <Menu size={22} strokeWidth={1.8} />
        </button>

        <a
          href="#/overview"
          onClick={(e) => {
            e.preventDefault()
            onHome()
          }}
          aria-label="InvestWatch — strona główna"
        >
          <span className="hidden sm:inline">
            <Logo />
          </span>
          <span className="sm:hidden">
            <Logo compact />
          </span>
        </a>

        <div className="ml-auto flex items-center gap-3">
          <Tooltip
            side="bottom"
            align="end"
            content="Powiadomienia przez WebSocket: nowe alerty wysokiego ryzyka, postęp skanowania i zmiany progów pojawiają się bez odświeżania strony."
          >
            <span
              tabIndex={0}
              className={`hidden cursor-help items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold md:inline-flex ${
                status === 'open' ? 'border-ok/30 bg-ok/10 text-ok' : 'border-warn-line bg-warn-bg text-warn-text'
              }`}
            >
              <Radio size={13} strokeWidth={2} aria-hidden />
              {status === 'open' ? 'Na żywo' : status === 'connecting' ? 'Łączenie…' : 'Offline'}
            </span>
          </Tooltip>
          <div className="flex items-center rounded-lg border border-line bg-surface-2 p-0.5" role="group" aria-label="Rozmiar tekstu">
            <button
              type="button"
              onClick={text.decrease}
              disabled={!text.canDecrease}
              aria-label="Zmniejsz tekst"
              className="rounded-md px-2.5 py-1 text-sm font-semibold text-ink-muted hover:bg-white hover:text-navy-800 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              A−
            </button>
            <button
              type="button"
              onClick={text.increase}
              disabled={!text.canIncrease}
              aria-label="Powiększ tekst"
              className="rounded-md px-2.5 py-1 text-sm font-semibold text-ink-muted hover:bg-white hover:text-navy-800 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
            >
              A+
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
