import { FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { api } from '../../api/client'
import { buttonClass, inputClass, ModuleBadge } from '../../components/ui/PageHeader'
import { RiskBadge } from '../../components/ui/RiskBadge'
import { Section } from '../../components/ui/Section'
import { ruleStatusMeta, riskMeta } from '../../lib/risk'
import type { AdhocResult } from '../../types'

const SAMPLE = `<p class="ad-label">Reklama</p>
<h1>Zarabiaj 20% rocznie na obligacjach!</h1>
<p>Oferta zatwierdzona przez KNF — w pełni bezpieczna inwestycja. Dom Maklerski Nordwisła S.A.</p>
<footer><small style="color:#cccccc">Inwestowanie wiąże się z ryzykiem utraty kapitału.</small></footer>`

/** Paste text or HTML and run all 18 criteria instantly — nothing is stored. */
export function AdhocCheck() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState<AdhocResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      const isHtml = /<\w+[^>]*>/.test(input)
      setResult(await api.analyze(isHtml ? { html: input } : { text: input }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Sprawdź materiał"
      description="Wklej tekst lub kod HTML reklamy — silnik oceni go natychmiast według 18 kryteriów. Wynik nie jest zapisywany."
      actions={
        <button type="button" onClick={() => setInput(SAMPLE)} className={buttonClass.ghost}>
          Wstaw przykład
        </button>
      }
    >
      <div className="grid gap-6 px-5 py-5 sm:px-6 lg:grid-cols-2">
        <div>
          <label htmlFor="adhoc" className="sr-only">
            Treść materiału
          </label>
          <textarea
            id="adhoc"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={10}
            placeholder="Np. treść posta, opis reklamy lub kod HTML strony…"
            className={`${inputClass} font-mono text-[0.8125rem]`}
          />
          <button type="button" onClick={run} disabled={busy || !input.trim()} className={`${buttonClass.primary} mt-3`}>
            <FlaskConical size={16} /> {busy ? 'Analizuję…' : 'Analizuj materiał'}
          </button>
          {error && <p className="mt-2 text-sm text-risk-critical-text">{error}</p>}
        </div>
        <div className="min-w-0">
          {!result && <p className="rounded-lg bg-surface px-4 py-6 text-center text-sm text-ink-muted">Tu pojawi się wynik analizy.</p>}
          {result && result.assessments.length === 0 && (
            <p className="rounded-lg bg-surface px-4 py-6 text-center text-sm text-ink-muted">
              Materiał nie ma cech reklamy usług inwestycyjnych ani oferty doradczej — żaden moduł nie ma zastosowania.
            </p>
          )}
          <div className="space-y-4">
            {result?.assessments.map((a) => (
              <div key={a.module} className="rounded-lg border border-line p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <ModuleBadge module={a.module} />
                  <RiskBadge level={a.level} />
                  <span className={`ml-auto text-2xl font-bold tabular ${riskMeta[a.level].text}`}>{Math.round(a.score)}</span>
                </div>
                <p className="mt-2 text-sm font-semibold text-ink">{a.summary}</p>
                {a.rules.length > 0 && (
                  <ul className="mt-3 space-y-1.5">
                    {a.rules
                      .filter((r) => r.status === 'fail' || r.status === 'warn')
                      .map((r) => (
                        <li key={r.id} className="flex gap-2 text-sm">
                          <span className={`mt-1.5 size-2 shrink-0 rounded-full ${ruleStatusMeta[r.status].dot}`} aria-hidden />
                          <span>
                            <b className="text-ink">
                              {r.id}. {r.name}
                            </b>{' '}
                            <span className="text-ink-muted">— {r.detail}</span>
                          </span>
                        </li>
                      ))}
                  </ul>
                )}
                {a.signals.filter((s) => s.weight > 0).length > 0 && (
                  <ul className="mt-3 space-y-1 text-sm text-ink-muted">
                    {a.signals
                      .filter((s) => s.weight > 0)
                      .map((s) => (
                        <li key={s.code}>• {s.label}</li>
                      ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
          {result && <p className="mt-2 text-xs text-ink-subtle">Czas analizy: {result.elapsed_ms} ms</p>}
        </div>
      </div>
    </Section>
  )
}
