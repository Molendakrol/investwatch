import { useCallback, useEffect, useRef, useState } from 'react'
import { useLive, type Topic } from '../live/LiveProvider'

/**
 * Fetch hook that refetches when its dependencies change or when any of the
 * given live topics receives a WebSocket event. Keeps the previous data while
 * refreshing, so live updates never flash an empty screen.
 */
export function useQuery<T>(fetcher: () => Promise<T>, deps: unknown[], topics: Topic[] = []) {
  const { revisions } = useLive()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const seq = useRef(0)
  const revKey = topics.map((t) => revisions[t]).join(':')

  const run = useCallback(() => {
    const id = ++seq.current
    setLoading(true)
    fetcher()
      .then((d) => {
        if (id === seq.current) {
          setData(d)
          setError(null)
        }
      })
      .catch((e: Error) => id === seq.current && setError(e.message))
      .finally(() => id === seq.current && setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    run()
  }, [run, revKey])

  return { data, error, loading, refetch: run }
}
