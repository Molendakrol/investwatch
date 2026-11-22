"""Optional local LLM (Ollama) — second opinion for Module 3.

Enabled only when OLLAMA_URL is set. Runs fully on-premise; any failure or
timeout falls back silently to the rule + embedding pipeline.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

log = logging.getLogger("analyzer.llm")

OLLAMA_URL = os.getenv("OLLAMA_URL", "").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

PROMPT = """Jesteś analitykiem nadzoru finansowego. Oceń, czy poniższy tekst oferuje
spersonalizowane doradztwo inwestycyjne (rekomendacje kupna/sprzedaży/trzymania
instrumentów finansowych dopasowane do klienta). Odpowiedz wyłącznie JSON:
{{"advice_probability": <0..1>, "reason": "<jedno zdanie po polsku>"}}

TEKST:
{text}
"""


def enabled() -> bool:
    return bool(OLLAMA_URL)


def advice_probability(text: str) -> tuple[float | None, str | None]:
    if not OLLAMA_URL:
        return None, None
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": PROMPT.format(text=text[:4000]), "stream": False, "format": "json"},
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "20")),
        )
        r.raise_for_status()
        data = json.loads(r.json().get("response", "{}"))
        return float(data.get("advice_probability", 0)), str(data.get("reason", ""))[:300]
    except Exception as exc:  # noqa: BLE001 — the LLM is strictly optional
        log.warning("ollama unavailable: %s", exc)
        return None, None
