const numberFmt = new Intl.NumberFormat('pl-PL')

export const formatNumber = (n: number) => numberFmt.format(n)

/** Polish plural form: 1 materiał, 2 materiały, 5 materiałów. */
export function plural(n: number, one: string, few: string, many: string): string {
  if (n === 1) return one
  const lastTwo = n % 100
  const last = n % 10
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return few
  return many
}

export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return '—'
  const minutes = Math.round((now - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return 'przed chwilą'
  if (minutes < 60) return `${minutes} min temu`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} godz. temu`
  const days = Math.floor(hours / 24)
  return `${days} ${plural(days, 'dzień', 'dni', 'dni')} temu`
}

export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
    timeZone: 'Europe/Warsaw',
  })
}

export function clockTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Warsaw' })
}

export const formatPercent = (value: number, digits = 0) => `${(value * 100).toFixed(digits).replace('.', ',')}%`

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
