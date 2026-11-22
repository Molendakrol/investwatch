"""Analyzer HTTP service (stateless). POST /analyze -> unified assessments."""

from __future__ import annotations

import logging
import os
import threading
import time

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import llm
from .engine import VERSION, analyze
from .register import DEMO_ENTRIES, Register, RegisterEntry
from .rules_m2 import SPECS

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("analyzer")

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")
REGISTER_TTL = int(os.getenv("REGISTER_TTL_SECONDS", "60"))

app = FastAPI(title="InvestWatch Analyzer", version=VERSION)


class RegisterCache:
    def __init__(self) -> None:
        self._register = Register(list(DEMO_ENTRIES))
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def get(self) -> Register:
        if time.time() - self._loaded_at > REGISTER_TTL:
            with self._lock:
                if time.time() - self._loaded_at > REGISTER_TTL:
                    self._refresh()
        return self._register

    def _refresh(self) -> None:
        self._loaded_at = time.time()
        try:
            r = httpx.get(f"{API_URL}/internal/register", headers={"X-Internal-Token": INTERNAL_TOKEN}, timeout=5)
            r.raise_for_status()
            entries = [RegisterEntry(e["name"], e["category"], e.get("scope", ""), e.get("source_url", "")) for e in r.json()]
            names = {e.name for e in entries}
            entries += [d for d in DEMO_ENTRIES if d.name not in names]
            self._register = Register(entries)
            log.info("register loaded: %d entities", len(entries))
        except Exception as exc:  # noqa: BLE001
            log.warning("register refresh failed, keeping %d cached entities: %s", len(self._register), exc)


registers = RegisterCache()


class AnalyzeIn(BaseModel):
    url: str
    html: str | None = None
    text: str | None = Field(default=None, description="Plain text (social posts)")
    author: str | None = None
    title: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": VERSION, "register_size": len(registers.get()), "llm": llm.enabled()}


@app.get("/rules")
def rules() -> list[dict]:
    return [{"id": s.id, "name": s.name, "legal_basis": s.legal_basis, "weight": s.weight, "description": s.description}
            for s in SPECS.values()]


@app.post("/analyze")
def analyze_endpoint(body: AnalyzeIn) -> dict:
    t0 = time.perf_counter()
    result = analyze(url=body.url, html=body.html, text=body.text, author=body.author, title=body.title,
                     register=registers.get())
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return result
