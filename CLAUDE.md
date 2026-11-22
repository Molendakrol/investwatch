# Wskazówki dla asystentów AI

- Usługi są niezależne: `frontend/` (React+TS), `services/api`, `services/worker`, `services/analyzer` (Python). Nie importuj kodu między usługami — komunikacja tylko przez HTTP.
- Interfejs po polsku, styl zgodny z `frontend/src/index.css` (tokeny `navy-*`, `ink-*`, `risk-*`).
- Po zmianie reguł uruchom `python -m unittest discover -s services/analyzer/tests -v`; precyzja i pełność nie mogą spaść.
- Przed oddaniem: `cd frontend && npm run build && npm audit` oraz `pip-audit -r services/*/requirements.txt`.
- Korpus testowy generuje `python demo-sites/generate.py`; dane mają być fikcyjne.
- Sekrety tylko w `.env`. Zeskanowanej treści nigdy nie renderuj jako HTML w panelu.
