import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { STATUSES, statusMeta } from '../../lib/risk'
import { useLive } from '../../live/LiveProvider'
import type { FindingStatus } from '../../types'

export function StatusPill({ status }: { status: FindingStatus }) {
  const m = statusMeta[status]
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${m.className}`}>{m.label}</span>
}

/** Status workflow control. Persists immediately; other dashboards update over WebSocket. */
export function StatusSelect({ id, status, onChanged }: { id: number; status: FindingStatus; onChanged?: (s: FindingStatus) => void }) {
  const [value, setValue] = useState(status)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { bump } = useLive()

  useEffect(() => setValue(status), [status])

  const change = async (next: FindingStatus) => {
    const prev = value
    setValue(next)
    setSaving(true)
    setError(null)
    try {
      await api.setStatus(id, next)
      onChanged?.(next)
      bump('findings', 'activity')
    } catch (e) {
      setValue(prev)
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div role="radiogroup" aria-label="Status sprawy" className="flex flex-wrap gap-1.5">
        {STATUSES.map((s) => {
          const active = s === value
          return (
            <button
              key={s}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={saving}
              onClick={() => !active && change(s)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                active ? 'bg-navy-800 text-white' : 'border border-line bg-white text-ink-muted hover:border-navy-600 hover:text-navy-800'
              }`}
            >
              {statusMeta[s].label}
            </button>
          )
        })}
      </div>
      {error && <p className="mt-1.5 text-xs text-risk-critical-text">Nie zapisano: {error}</p>}
    </div>
  )
}
