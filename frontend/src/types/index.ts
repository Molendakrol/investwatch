export type RiskLevel = 'critical' | 'high' | 'medium' | 'low'
export type ModuleId = 'm1' | 'm2' | 'm3'
export type FindingStatus = 'new' | 'in_review' | 'escalated' | 'closed' | 'false_positive'

export type RouteId = 'overview' | 'alerts' | 'm1' | 'm2' | 'm3' | 'sources' | 'calibration'

export interface Route {
  id: RouteId
  params: URLSearchParams
}

export interface NavItem {
  id: RouteId
  label: string
  description: string
  badge?: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export type Thresholds = Record<ModuleId, number>

export interface DocumentRef {
  id: number
  url: string
  platform: string
  title: string
  author: string | null
  site_name: string | null
  published_at: string | null
  first_seen: string
  last_seen: string
  excerpt: string
  scan_count: number
  change_count: number
  duplicate_of: number | null
  text?: string
  content_hash?: string
  has_raw?: boolean
}

export interface RuleResult {
  id: string
  name: string
  status: 'pass' | 'fail' | 'warn' | 'na'
  detail: string
  legal_basis: string
  weight: number
  evidence: string[]
}

export interface Signal {
  code: string
  label: string
  weight: number
  evidence: string
}

export interface Finding {
  id: number
  module: ModuleId
  score: number
  level: RiskLevel
  status: FindingStatus
  summary: string
  entity: string | null
  firm: string | null
  firm_category: string | null
  is_alert: boolean
  created_at: string
  updated_at: string
  document: DocumentRef
  top_signals: string[]
  signals?: Signal[]
  rules?: RuleResult[]
  related?: { id: number; module: ModuleId; score: number; summary: string }[]
}

export interface FindingsResponse {
  total: number
  items: Finding[]
  thresholds: Thresholds
  platforms: string[]
}

export interface Stats {
  generated_at: string
  days: number
  thresholds: Thresholds
  kpi: {
    documents: number
    documents_in_range: number
    alerts: number
    critical: number
    open: number
    escalated: number
    by_module: Record<ModuleId, number>
    by_level: Record<RiskLevel, number>
    jobs_24h: number
    jobs_failed_24h: number
    queue: number
  }
  timeline: { date: string; counts: Record<RiskLevel, number> }[]
  top_rules: { id: string; name: string; legal_basis: string; count: number }[]
  top_signals: { module: ModuleId; code: string; label: string; count: number }[]
  sources: { total: number; active: number; failed: number; never_run: number }
  last_sweep: string | null
  register: RegisterSummary
}

export interface RegisterSummary {
  total: number
  by_category: Record<string, number>
  fetched_at: string | null
}

export interface Source {
  id: number
  url: string
  kind: 'html' | 'social' | 'meta_ads' | 'knf_register'
  name: string
  group: 'register' | 'demo' | 'web' | 'social'
  active: boolean
  created_at: string
  last_run_at: string | null
  last_status: 'done' | 'failed' | null
  last_error: string | null
  items_found: number
}

export interface Job {
  id: number
  source_id: number | null
  url: string
  kind: Source['kind']
  status: 'queued' | 'running' | 'done' | 'failed'
  trigger: string
  attempts: number
  worker: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  result_count: number
  error: string | null
}

export interface ActivityEvent {
  id: number
  ts: string
  kind: 'sweep' | 'flag' | 'system' | 'analyst'
  message: string
}

export interface CalibrationItem {
  url: string
  note: string
  label: boolean
  score: number
  finding_id: number | null
  title: string
}

export interface CurvePoint {
  t: number
  tp: number
  fp: number
  fn: number
  tn: number
  precision: number
  recall: number
  f1: number
}

export interface Calibration {
  module: ModuleId
  threshold: number
  items: CalibrationItem[]
  curve: CurvePoint[]
  recommended: number | null
  labelled: number
  scores_all: number[]
}

export interface RegisterEntity {
  id: number
  name: string
  category: string
  address: string
  license_date: string
  scope: string
  source_url: string
  fetched_at: string
}

export interface Health {
  api: string
  analyzer: string
  websocket_clients: number
  last_worker_activity: string | null
  database: string
}

export interface AdhocResult {
  document: { title: string; excerpt: string; blocks: number }
  assessments: {
    module: ModuleId
    score: number
    level: RiskLevel
    summary: string
    entity: string | null
    firm: string | null
    signals: Signal[]
    rules: RuleResult[]
  }[]
  elapsed_ms: number
}

export interface CheckResult {
  status: 'done' | 'failed' | 'timeout'
  error: string | null
  duration_ms?: number | null
  documents: { id: number; url: string; title: string; author: string | null; platform: string; excerpt: string }[]
  findings: Finding[]
}
