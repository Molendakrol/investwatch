# InvestWatch — na straży inwestorów

System monitoringu treści inwestycyjnych w sieci dla UKNF (HackNation 2026). Scraper pobiera strony, posty i reklamy,
silnik analizy ocenia je w trzech modułach, a panel webowy pokazuje wyniki na żywo.

| Moduł | Co wykrywa |
|---|---|
| **M1** Ekosystem zewnętrzny | reklamy firm z rejestru UKNF u finfluencerów i podmiotów trzecich (firma, reklamujący, treść, URL) |
| **M2** Informacja o ryzyku | materiały firm inwestycyjnych niespełniające 18 kryteriów (art. 44 rozp. del. 2017/565, MiFID II) |
| **M3** Doradztwo bez zezwolenia | oferty wealth management / family office / „sygnałów” od podmiotów spoza rejestru |

## Quick Start

```bash
cp .env.example .env          # zmień POSTGRES_PASSWORD i INTERNAL_TOKEN
docker compose up --build
```

- Panel: http://localhost:3000
- API (OpenAPI): http://localhost:8000/docs
- Korpus testowy: http://localhost:8080

Po starcie system sam pobiera rejestr firm inwestycyjnych z knf.gov.pl, a następnie skanuje korpus testowy.
Pierwsze alerty pojawiają się po ok. 30 s.

**Sprawdź link** (strona główna panelu): wklej adres strony lub filmu YouTube — wynik w kilka sekund. Facebook, Instagram, TikTok, X i LinkedIn nie udostępniają treści bez logowania (robots.txt / logowanie); wtedy panel pozwala wkleić treść posta.

Lokalny model językowy (opcjonalnie, druga opinia w M3):

```bash
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull gemma3:4b
# w .env: OLLAMA_URL=http://ollama:11434, potem: docker compose up -d analyzer
```

Bez Dockera (Python 3.11+, Node 20+): `./scripts/dev.sh` → panel na http://localhost:8000 (zbudowany panel serwuje API) lub http://localhost:5173 (tryb deweloperski). SQLite zamiast PostgreSQL.

## Wymagania sprzętowe

| Wariant | CPU | RAM | Dysk |
|---|---|---|---|
| Podstawowy (reguły + embeddingi) | 2 rdzenie | 2 GB | 2 GB |
| Z lokalnym LLM (`--profile llm`, gemma3:1b–4b) | 4 rdzenie | 8 GB (lub GPU 6 GB) | +8 GB (obraz Ollama + model) |

## Usługi

| Usługa | Port | Rola |
|---|---|---|
| `frontend` | 3000 | React + Vite (nginx), proxy `/api` i `/ws` |
| `api` | 8000 | FastAPI: REST, WebSocket, kolejka zadań, harmonogram, PostgreSQL, magazyn obiektów (kopie dowodowe) |
| `worker` | — | scraper: kolektory HTML / social / Meta Ad Library / rejestr UKNF, rotacja User-Agent i proxy, robots.txt |
| `analyzer` | 8001 (wewn.) | silnik analizy: preprocessing, embeddingi, reguły M2, moduły M1 i M3, opcjonalnie Ollama |
| `postgres` | — | baza metadanych i treści |
| `demo-sites` | 8080 | korpus testowy z etykietami (fikcyjne podmioty) do kalibracji |
| `ollama` | — | opcjonalny lokalny LLM (profil `llm`) |

## Konfiguracja (`.env`)

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `POSTGRES_PASSWORD`, `INTERNAL_TOKEN` | — | sekrety (tylko w `.env`, nie w repozytorium) |
| `SWEEP_INTERVAL_MINUTES` | 30 | co ile minut harmonogram skanuje aktywne źródła |
| `REGISTER_INTERVAL_HOURS` | 24 | odświeżanie rejestru firm inwestycyjnych UKNF |
| `DEFAULT_THRESHOLD` | 50 | początkowy próg alertu (zmieniany w panelu Kalibracja) |
| `WORKER_CONCURRENCY` | 3 | liczba równoległych zadań workera |
| `FETCH_MIN_INTERVAL_SECONDS` | 1.0 | minimalny odstęp zapytań do jednego hosta |
| `RESPECT_ROBOTS` | true | respektowanie robots.txt |
| `PROXIES` | — | pula proxy rotowana per zapytanie (`http://h1:3128,http://h2:3128`) |
| `OLLAMA_URL`, `OLLAMA_MODEL` | — / gemma3:4b | lokalny LLM (puste = wyłączony) |

## Testy i bezpieczeństwo

```bash
python -m unittest discover -s services/analyzer/tests -v   # jakość na korpusie z etykietami
cd frontend && npm run build                                 # TypeScript + build
cd frontend && npm audit                                     # 0 podatności
pip-audit -r services/api/requirements.txt                   # 0 podatności (analogicznie analyzer, worker)
```

Więcej: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) · [docs/PROCES_AI.md](docs/PROCES_AI.md)
