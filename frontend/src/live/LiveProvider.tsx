import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { Finding } from '../types'

export type Topic = 'findings' | 'jobs' | 'sources' | 'settings' | 'activity' | 'register'
type Revisions = Record<Topic, number>

export interface Toast {
  key: number
  finding: Finding
}

interface LiveContextValue {
  status: 'connecting' | 'open' | 'closed'
  revisions: Revisions
  toasts: Toast[]
  dismissToast: (key: number) => void
  bump: (...topics: Topic[]) => void
}

const LiveContext = createContext<LiveContextValue | null>(null)

const EVENT_TOPICS: Record<string, Topic[]> = {
  finding: ['findings'],
  alert: ['findings'],
  job: ['jobs'],
  source: ['sources'],
  settings: ['settings', 'findings'],
  activity: ['activity'],
  register: ['register'],
  reset: ['findings', 'jobs', 'sources', 'activity'],
}

const INITIAL: Revisions = { findings: 0, jobs: 0, sources: 0, settings: 0, activity: 0, register: 0 }

export function LiveProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<LiveContextValue['status']>('connecting')
  const [revisions, setRevisions] = useState<Revisions>(INITIAL)
  const [toasts, setToasts] = useState<Toast[]>([])
  const pending = useRef<Set<Topic>>(new Set())
  const flushTimer = useRef<number | null>(null)
  const toastKey = useRef(0)

  // Coalesce bursts of events (a sweep emits dozens) into one refetch per topic.
  const bump = useCallback((...topics: Topic[]) => {
    topics.forEach((t) => pending.current.add(t))
    if (flushTimer.current !== null) return
    flushTimer.current = window.setTimeout(() => {
      const topicsNow = [...pending.current]
      pending.current.clear()
      flushTimer.current = null
      setRevisions((r) => {
        const next = { ...r }
        topicsNow.forEach((t) => (next[t] += 1))
        return next
      })
    }, 400)
  }, [])

  const dismissToast = useCallback((key: number) => setToasts((t) => t.filter((x) => x.key !== key)), [])

  useEffect(() => {
    let ws: WebSocket | null = null
    let retry = 0
    let closedByUs = false
    let ping: number | undefined
    let reconnect: number | undefined

    const connect = () => {
      setStatus('connecting')
      ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
      ws.onopen = () => {
        retry = 0
        setStatus('open')
        bump('findings', 'jobs', 'sources', 'activity', 'settings', 'register')
        ping = window.setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send('ping'), 25000)
      }
      ws.onmessage = (e) => {
        let msg: { type: string; payload: unknown }
        try {
          msg = JSON.parse(e.data)
        } catch {
          return
        }
        const topics = EVENT_TOPICS[msg.type]
        if (topics) bump(...topics)
        if (msg.type === 'alert') {
          const f = msg.payload as Finding
          if (f.level === 'critical' || f.level === 'high') {
            const key = ++toastKey.current
            setToasts((t) => [...t.slice(-3), { key, finding: f }])
            window.setTimeout(() => setToasts((t) => t.filter((x) => x.key !== key)), 9000)
          }
        }
      }
      ws.onclose = () => {
        window.clearInterval(ping)
        if (closedByUs) return
        setStatus('closed')
        reconnect = window.setTimeout(connect, Math.min(10000, 1000 * 2 ** retry++))
      }
      ws.onerror = () => ws?.close()
    }
    // Deferred one tick: React StrictMode mounts effects twice in development, and closing a
    // socket that is still connecting would log a spurious error in the console.
    const start = window.setTimeout(connect, 0)
    return () => {
      closedByUs = true
      window.clearTimeout(start)
      window.clearInterval(ping)
      window.clearTimeout(reconnect)
      ws?.close()
    }
  }, [bump])

  const value = useMemo(() => ({ status, revisions, toasts, dismissToast, bump }), [status, revisions, toasts, dismissToast, bump])
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>
}

export function useLive() {
  const ctx = useContext(LiveContext)
  if (!ctx) throw new Error('useLive must be used inside LiveProvider')
  return ctx
}
