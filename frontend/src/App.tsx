import { useCallback, useEffect, useState } from 'react'
import { Toasts } from './components/Toasts'
import { routeTitles } from './data/navigation'
import { FindingContext } from './features/findings/FindingContext'
import { FindingDrawer } from './features/findings/FindingDrawer'
import { useHashRoute } from './hooks/useHashRoute'
import { AppShell } from './layouts/AppShell'
import { AlertsPage } from './pages/AlertsPage'
import { CalibrationPage } from './pages/CalibrationPage'
import { ModulePage } from './pages/ModulePage'
import { OverviewPage } from './pages/OverviewPage'
import { SourcesPage } from './pages/SourcesPage'

export default function App() {
  const { route, navigate } = useHashRoute()
  const [findingId, setFindingId] = useState<number | null>(null)
  const closeDrawer = useCallback(() => setFindingId(null), [])

  useEffect(() => {
    document.title = `${routeTitles[route.id]} — InvestWatch`
  }, [route.id])

  // Deep link to a case: #/alerts?f=12 opens its details directly (shareable between analysts).
  const linked = route.params.get('f')
  useEffect(() => {
    if (linked && /^\d+$/.test(linked)) setFindingId(Number(linked))
  }, [linked])

  let page
  switch (route.id) {
    case 'alerts':
      page = <AlertsPage key={route.params.toString()} onNavigate={navigate} initial={route.params} />
      break
    case 'm1':
    case 'm2':
    case 'm3':
      page = <ModulePage key={route.id} module={route.id} onNavigate={navigate} />
      break
    case 'sources':
      page = <SourcesPage onNavigate={navigate} />
      break
    case 'calibration':
      page = <CalibrationPage onNavigate={navigate} />
      break
    default:
      page = <OverviewPage onNavigate={navigate} />
  }

  return (
    <FindingContext.Provider value={setFindingId}>
      <AppShell route={route.id} onNavigate={navigate}>
        {page}
        <footer className="mt-12 border-t border-line pt-5 text-sm leading-relaxed text-ink-muted">
          InvestWatch — prototyp systemu monitoringu treści inwestycyjnych, HackNation 2026. Nie jest oficjalnym serwisem żadnej instytucji.
          Rejestr firm inwestycyjnych pobierany jest z knf.gov.pl; korpus testowy zawiera wyłącznie fikcyjne podmioty i treści.
        </footer>
      </AppShell>
      {findingId !== null && <FindingDrawer id={findingId} onClose={closeDrawer} onOpen={setFindingId} />}
      <Toasts />
    </FindingContext.Provider>
  )
}
