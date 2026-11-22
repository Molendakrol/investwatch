import { Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { Tooltip } from './Tooltip'

/** Small "what does this mean" affordance next to labels. */
export function InfoHint({ children, align = 'center' }: { children: ReactNode; align?: 'center' | 'start' | 'end' }) {
  return (
    <Tooltip content={children} align={align}>
      <button
        type="button"
        aria-label="Więcej informacji"
        className="inline-flex text-ink-subtle transition-colors hover:text-navy-700 focus-visible:text-navy-700"
      >
        <Info size={14} strokeWidth={1.75} />
      </button>
    </Tooltip>
  )
}
