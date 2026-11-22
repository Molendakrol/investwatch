import type { FindingStatus, RiskLevel, RuleResult } from '../types'

export const RISK_LEVELS: RiskLevel[] = ['critical', 'high', 'medium', 'low']

export const riskMeta: Record<
  RiskLevel,
  { label: string; text: string; bg: string; tint: string; fill: string; description: string }
> = {
  critical: {
    label: 'Krytyczne',
    text: 'text-risk-critical-text',
    bg: 'bg-risk-critical',
    tint: 'bg-risk-critical/10',
    fill: 'var(--color-risk-critical)',
    description: 'Ocena ≥ 85. Wiele poważnych sygnałów — wymaga pilnej weryfikacji.',
  },
  high: {
    label: 'Wysokie',
    text: 'text-risk-high-text',
    bg: 'bg-risk-high',
    tint: 'bg-risk-high/12',
    fill: 'var(--color-risk-high)',
    description: 'Ocena 70–84. Wyraźne naruszenia lub silne sygnały.',
  },
  medium: {
    label: 'Średnie',
    text: 'text-risk-medium-text',
    bg: 'bg-risk-medium',
    tint: 'bg-risk-medium/18',
    fill: 'var(--color-risk-medium)',
    description: 'Ocena 50–69. Sygnały wymagające oceny w kontekście.',
  },
  low: {
    label: 'Niskie',
    text: 'text-risk-low-text',
    bg: 'bg-risk-low',
    tint: 'bg-risk-low/20',
    fill: 'var(--color-risk-low)',
    description: 'Ocena < 50. Pojawia się tylko, gdy próg alertu jest obniżony.',
  },
}

export const STATUSES: FindingStatus[] = ['new', 'in_review', 'escalated', 'closed', 'false_positive']

export const statusMeta: Record<FindingStatus, { label: string; className: string }> = {
  new: { label: 'Nowy', className: 'bg-navy-50 text-navy-800' },
  in_review: { label: 'W weryfikacji', className: 'bg-warn-bg text-warn-text' },
  escalated: { label: 'Eskalowany', className: 'bg-risk-critical/10 text-risk-critical-text' },
  closed: { label: 'Zamknięty', className: 'bg-ok/10 text-ok' },
  false_positive: { label: 'Fałszywy alarm', className: 'bg-surface text-ink-muted ring-1 ring-inset ring-line' },
}

export const ruleStatusMeta: Record<RuleResult['status'], { label: string; className: string; dot: string }> = {
  fail: { label: 'Naruszenie', className: 'text-risk-critical-text', dot: 'bg-risk-critical' },
  warn: { label: 'Uwaga', className: 'text-risk-high-text', dot: 'bg-risk-high' },
  pass: { label: 'Spełnione', className: 'text-ok', dot: 'bg-ok' },
  na: { label: 'Nie dotyczy', className: 'text-ink-subtle', dot: 'bg-line-strong' },
}

export const registerCategoryLabel: Record<string, string> = {
  dom_maklerski: 'Dom maklerski',
  bank: 'Bank (działalność maklerska)',
  oddzial: 'Oddział firmy zagranicznej',
  transgraniczna: 'Firma zagraniczna (transgranicznie)',
  demo: 'Podmiot fikcyjny (korpus testowy)',
}

export const sourceKindLabel: Record<string, string> = {
  html: 'Strona WWW',
  social: 'Post (social media)',
  meta_ads: 'Meta Ad Library',
  knf_register: 'Rejestr UKNF',
}
