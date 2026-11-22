import { useCallback, useEffect, useState } from 'react'
import type { Route, RouteId } from '../types'

const ROUTES: RouteId[] = ['overview', 'alerts', 'm1', 'm2', 'm3', 'sources', 'calibration']

function parse(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#\/?/, '').split('?')
  const id = (ROUTES.includes(path as RouteId) ? path : 'overview') as RouteId
  return { id, params: new URLSearchParams(query) }
}

/** Minimal hash router: linkable views with query params, back/forward friendly. */
export function useHashRoute() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash))

  useEffect(() => {
    const onChange = () => {
      const next = parse(window.location.hash)
      setRoute((prev) => {
        if (prev.id !== next.id) window.scrollTo({ top: 0 })
        return next
      })
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  const navigate = useCallback((id: RouteId, params?: Record<string, string>) => {
    const q = params ? new URLSearchParams(params).toString() : ''
    window.location.hash = `/${id}${q ? `?${q}` : ''}`
  }, [])

  return { route, navigate }
}
