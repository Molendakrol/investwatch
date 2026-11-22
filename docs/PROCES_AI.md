# Proces wytwarzania z asystentem AI

Projekt powstał w parze: jeden programista + asystent kodowania (Claude Code). Asystent pisał kod,
programista ustalał kierunek, akceptował decyzje i oceniał wynik. Każda iteracja przechodziła ten sam cykl.

## Cykl iteracji

| Krok | Co się dzieje | Artefakt / bramka |
|---|---|---|
| 1. Specyfikacja | Opis wyzwania, załączniki (kryteria ryzyka, definicje, rejestr) wczytane do kontekstu asystenta | dokumenty UKNF |
| 2. Plan | Asystent rozpisuje plan kroków i architekturę; człowiek akceptuje lub koryguje | lista zadań |
| 3. Implementacja pionowa | Jeden przepływ od danych do UI naraz (np. korpus → silnik → API → widok) | kod |
| 4. Weryfikacja automatyczna | `tsc`, `npm run build`, test jakości na korpusie z etykietami, `npm audit`, `pip-audit` | zero błędów, P/R ≥ progi testu |
| 5. Weryfikacja w przeglądarce | Asystent uruchamia stos, klika interfejs, robi zrzuty (desktop i mobile), czyta konsolę | brak błędów w konsoli |
| 6. Przegląd człowieka | Programista ocenia wygląd i zachowanie; uwagi wracają do kroku 2 | decyzja |

## Zasady

- **Najpierw dane z etykietami, potem reguły.** Korpus testowy (`demo-sites/generate.py`) ma etykiety, a test
  `services/analyzer/tests/test_corpus.py` pilnuje precyzji i pełności — zmiana reguły, która pogarsza wynik, nie przechodzi.
- **Wyjaśnialność zamiast czarnej skrzynki.** Każda ocena to suma jawnych sygnałów z dowodem (cytatem) i podstawą prawną.
- **Bezpieczeństwo jako bramka.** Skan zależności przed każdym oddaniem; sekrety tylko w `.env`; scraper z ochroną SSRF,
  limitami rozmiaru i respektowaniem robots.txt; zeskanowany HTML nigdy nie jest renderowany w panelu (podgląd jako tekst).
- **Uczciwość danych.** Wszystkie podmioty w korpusie są fikcyjne; rzeczywiste są tylko dane z rejestru UKNF.

## Przykłady korekt wykrytych w procesie

- Pierwszy przebieg testu korpusu: precyzja 1,00, pełność 0,70. Analiza błędów pokazała, że nagłówek
  `<summary>` z hasłem „ryzyko” był liczony jako ostrzeżenie, a ostrzeżenie w innym języku zaliczało regułę 3.
  Po poprawkach: pełność 0,90 przy progu 50 i 1,00 przy progu rekomendowanym.
- Rejestr UKNF jest stronicowany — weryfikacja liczby podmiotów wykazała brak kolejnych stron; dodano obsługę `?page=N`
  (z ~90 do ponad 850 podmiotów).
- `pip-audit` wykrył podatności w starszej wersji Starlette — podniesiono FastAPI/Uvicorn i powtórzono testy.
- Test `docker compose up` od zera wykrył błąd niewidoczny lokalnie: API szukało katalogu repozytorium, którego
  w kontenerze nie ma, i nie startowało. Poprawka w `services/api/app/config.py`, ponowny test: 6 kontenerów,
  PostgreSQL, 858 podmiotów z rejestru UKNF, 32/32 zadania, te same wyniki jakości co lokalnie.
