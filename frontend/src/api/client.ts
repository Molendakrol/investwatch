import type {
  ActivityEvent,
  CheckResult,
  AdhocResult,
  Calibration,
  Finding,
  FindingsResponse,
  FindingStatus,
  Health,
  Job,
  ModuleId,
  RegisterEntity,
  RegisterSummary,
  Source,
  Stats,
  Thresholds,
} from '../types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  } catch {
    throw new ApiError(0, 'Brak połączenia z API. Sprawdź, czy usługa api działa.')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export interface FindingFilters {
  module?: string
  level?: string
  status?: string
  platform?: string
  q?: string
  date_from?: string
  date_to?: string
  sort?: 'score' | 'date'
  include_below_threshold?: boolean
}

export const api = {
  health: () => request<Health>('/api/health'),
  stats: (days: number) => request<Stats>(`/api/stats${qs({ days })}`),
  findings: (f: FindingFilters = {}) => request<FindingsResponse>(`/api/findings${qs({ ...f })}`),
  finding: (id: number) => request<Finding>(`/api/findings/${id}`),
  setStatus: (id: number, status: FindingStatus) =>
    request<Finding>(`/api/findings/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  sources: () => request<Source[]>('/api/sources'),
  addSource: (url: string, kind: Source['kind']) =>
    request<{ source: Source; job: Job | null }>('/api/sources', { method: 'POST', body: JSON.stringify({ url, kind }) }),
  toggleSource: (id: number, active: boolean) =>
    request<Source>(`/api/sources/${id}`, { method: 'PATCH', body: JSON.stringify({ active }) }),
  runSource: (id: number) => request<{ job: Job | null; already_queued?: boolean }>(`/api/sources/${id}/run`, { method: 'POST' }),
  sweep: () => request<{ queued: number }>('/api/sweep', { method: 'POST' }),
  reset: () => request<{ queued: number }>('/api/admin/reset', { method: 'POST' }),
  jobs: (limit = 60) => request<Job[]>(`/api/jobs${qs({ limit })}`),
  activity: (limit = 20) => request<ActivityEvent[]>(`/api/activity${qs({ limit })}`),
  calibration: (module: ModuleId) => request<Calibration>(`/api/calibration${qs({ module })}`),
  settings: () => request<{ thresholds: Thresholds; sweep_interval_minutes: number; llm: boolean }>('/api/settings'),
  setThresholds: (t: Partial<Thresholds>) =>
    request<{ thresholds: Thresholds }>('/api/settings/thresholds', { method: 'PUT', body: JSON.stringify(t) }),
  register: (q?: string, category?: string) =>
    request<{ summary: RegisterSummary; items: RegisterEntity[] }>(`/api/register${qs({ q, category, limit: 200 })}`),
  check: (url: string) => request<CheckResult>('/api/check', { method: 'POST', body: JSON.stringify({ url }) }),
  analyze: (body: { text?: string; html?: string; url?: string; author?: string }) =>
    request<AdhocResult>('/api/analyze', { method: 'POST', body: JSON.stringify(body) }),
  reportUrl: (module: ModuleId) => `/api/reports/${module}.csv`,
  rawUrl: (docId: number) => `/api/documents/${docId}/raw`,
}
