import { ClipboardPaste, Link2, Loader2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../../api/client'
import { ModuleBadge, buttonClass, inputClass } from '../../components/ui/PageHeader'
import { RiskBadge } from '../../components/ui/RiskBadge'
import { modules } from '../../data/navigation'
import { riskMeta } from '../../lib/risk'
import { useLive } from '../../live/LiveProvider'
import type { AdhocResult, CheckResult, ModuleId, RiskLevel } from '../../types'
import { useOpenFinding } from '../findings/FindingContext'

interface CardProps {
  module: ModuleId
  level: RiskLevel
  score: number
  summary: string
  points: string[]
  isAlert: boolean | null
  onDetails?: () => void
}

function ResultCard({ module, level, score, summary, points, isAlert, onDetails }: CardProps) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <ModuleBadge module={module} />
        <span className="text-sm font-medium text-ink-muted">{modules[module].short}</span>
        <RiskBadge level={level} />
        <span className={`ml-auto text-3xl font-bold leading-none tabular ${riskMeta[level].text}`}>{Math.round(score)}</span>
      </div>
      <p className="mt-2 font-semibold leading-snug text-ink">{summary}</p>
      {points.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm text-ink-muted">
          {points.slice(0, 5).map((p) => (
            <li key={p}>• {p}</li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        <span className={isAlert ? 'font-semibold text-risk-critical-text' : 'text-ink-muted'}>
          {isAlert === null ? 'Analiza bez zapisu w rejestrze' : isAlert ? 'Powyżej progu — dodano do rejestru alertów' : 'Poniżej progu alertu'}
        </span>
        {onDetails && (
          <button type="button" onClick={onDetails} className="ml-auto text-sm font-semibold text-navy-700 hover:underline">
            Dowody i uzasadnienie →
          </button>
        )}
      </div>
    </div>
  )
}

function NoFindings() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-ok/30 bg-ok/5 p-4 text-sm">
      <ShieldCheck size={18} className="mt-0.5 shrink-0 text-ok" />
      <p className="text-ink">
        <b>Brak zastrzeżeń.</b> Treść nie dotyczy usług inwestycyjnych albo żaden moduł nie wykrył sygnałów ryzyka.
      </p>
    </div>
  )
}

/** Paste a link to a page or post → fetched by the scraper, analysed, result shown immediately. */
export function LinkCheck() {
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<CheckResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pasted, setPasted] = useState('')
  const [author, setAuthor] = useState('')
  const [manual, setManual] = useState<AdhocResult | null>(null)
  const open = useOpenFinding()
  const { bump } = useLive()

  /** Accepts "example.pl", "www.example.pl/abc" or a full URL; returns a full https URL or null. */
  const normalize = (raw: string): string | null => {
    const v = raw.trim().replace(/^<|>$/g, '')
    if (!v) return null
    const withScheme = /^https?:\/\//i.test(v) ? v : `https://${v.replace(/^\/+/, '')}`
    try {
      const u = new URL(withScheme)
      return u.hostname.includes('.') || u.hostname === 'localhost' ? u.toString() : null
    } catch {
      return null
    }
  }

  const check = async (e?: FormEvent, preset?: string) => {
    e?.preventDefault()
    const target = normalize(preset ?? url)
    if (!target) {
      setError('To nie wygląda na adres strony. Wklej np. strona-brokera.pl albo https://www.youtube.com/watch?v=…')
      return
    }
    setUrl(target)
    setBusy(true)
    setError(null)
    setResult(null)
    setManual(null)
    try {
      const r = await api.check(target)
      setResult(r)
      bump('findings', 'sources', 'jobs')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const analyzePasted = async () => {
    setBusy(true)
    setError(null)
    try {
      setManual(await api.analyze({ text: pasted, url: url.trim() || 'about:pasted', author: author.trim() || undefined }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // Deep link: #/overview?check=<url> runs the check on load (handy for demos and sharing).
  const autoRan = useRef(false)
  useEffect(() => {
    const preset = new URLSearchParams(window.location.hash.split('?')[1] ?? '').get('check')
    if (preset && !autoRan.current) {
      autoRan.current = true
      setUrl(preset)
      void check(undefined, preset)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const failed = result && result.status !== 'done'
  const doc = result?.documents[0]

  return (
    <section className="overflow-hidden rounded-xl border-2 border-navy-800/15 bg-white">
      <div className="border-b border-line bg-navy-50/60 px-5 py-4 sm:px-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-navy-900">
          <Link2 size={20} /> Sprawdź link
        </h2>
        <p className="mt-0.5 text-sm text-ink-muted">
          Wklej adres strony, artykułu, reklamy lub filmu na YouTube — system pobierze treść i oceni ją we wszystkich trzech modułach.
        </p>
      </div>
      <div className="px-5 py-5 sm:px-6">
        <form onSubmit={check} className="flex flex-col gap-3 sm:flex-row">
          <label className="flex-1">
            <span className="sr-only">Adres do sprawdzenia</span>
            <input
              type="text"
              inputMode="url"
              autoComplete="off"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="np. strona-brokera.pl albo https://…"
              className={`${inputClass} py-3 text-base`}
            />
          </label>
          <button type="submit" disabled={busy || !url.trim()} className={`${buttonClass.primary} justify-center px-6 py-3 text-base`}>
            {busy ? <Loader2 size={18} className="animate-spin" /> : <ShieldCheck size={18} />}
            {busy ? 'Pobieram i analizuję…' : 'Sprawdź'}
          </button>
        </form>
        <p className="mt-2 text-xs text-ink-muted">
          Facebook, Instagram, TikTok, X i LinkedIn nie udostępniają treści bez logowania — wtedy wklej treść posta, a analiza przebiegnie tak samo.
        </p>

        {error && <p className="mt-4 text-sm text-risk-critical-text">{error}</p>}

        {result && !failed && (
          <div className="mt-5 space-y-3">
            {doc && (
              <p className="text-sm text-ink-muted">
                <b className="text-ink">{doc.title || doc.url}</b>
                {doc.author && <> · autor: {doc.author}</>} · {doc.platform}
                {result.duration_ms != null && <> · {(result.duration_ms / 1000).toFixed(1).replace('.', ',')} s</>}
              </p>
            )}
            {result.findings.length === 0 && <NoFindings />}
            <div className="grid gap-3 lg:grid-cols-2">
              {result.findings.map((f) => (
                <ResultCard
                  key={f.id}
                  module={f.module}
                  level={f.level}
                  score={f.score}
                  summary={f.summary}
                  points={f.top_signals}
                  isAlert={f.is_alert}
                  onDetails={() => open(f.id)}
                />
              ))}
            </div>
          </div>
        )}

        {failed && (
          <div className="mt-5 rounded-lg border border-warn-line bg-warn-bg p-4">
            <p className="flex items-start gap-2 text-sm text-warn-text">
              <TriangleAlert size={18} className="mt-0.5 shrink-0" />
              <span>
                <b>Nie udało się pobrać treści.</b> {result.error}
              </span>
            </p>
            <div className="mt-4 space-y-3">
              <label className="block">
                <span className="text-xs font-medium text-ink-muted">Treść posta / reklamy (skopiuj z serwisu)</span>
                <textarea value={pasted} onChange={(e) => setPasted(e.target.value)} rows={5} className={`${inputClass} mt-1`} />
              </label>
              <label className="block max-w-sm">
                <span className="text-xs font-medium text-ink-muted">Autor / nazwa profilu (opcjonalnie)</span>
                <input value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="np. @nazwa.profilu" className={`${inputClass} mt-1`} />
              </label>
              <button type="button" onClick={analyzePasted} disabled={busy || !pasted.trim()} className={buttonClass.primary}>
                <ClipboardPaste size={16} /> Analizuj wklejoną treść
              </button>
            </div>
          </div>
        )}

        {manual && (
          <div className="mt-5 space-y-3">
            {manual.assessments.length === 0 && <NoFindings />}
            <div className="grid gap-3 lg:grid-cols-2">
              {manual.assessments.map((a) => (
                <ResultCard
                  key={a.module}
                  module={a.module}
                  level={a.level}
                  score={a.score}
                  summary={a.summary}
                  points={
                    a.rules.length
                      ? a.rules.filter((r) => r.status === 'fail').map((r) => `${r.id}. ${r.name}`)
                      : a.signals.filter((s) => s.weight > 0).map((s) => s.label)
                  }
                  isAlert={null}
                />
              ))}
            </div>
            <p className="text-xs text-ink-muted">Analiza wklejonej treści nie jest zapisywana w rejestrze.</p>
          </div>
        )}
      </div>
    </section>
  )
}
