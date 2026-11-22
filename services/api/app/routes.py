from __future__ import annotations

import csv
import io
import os
import socket
from datetime import timedelta
from typing import Iterator, Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import config, services as svc
from .db import Activity, Document, Finding, Job, RegisterEntity, SessionLocal, Source, utcnow
from .events import hub

ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8001").rstrip("/")

public = APIRouter(prefix="/api")
internal = APIRouter(prefix="/internal")


def db() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def require_internal(x_internal_token: str = Header(default="")) -> None:
    if x_internal_token != config.INTERNAL_TOKEN:
        raise HTTPException(401, "invalid internal token")


# ====================================================================== public

@public.get("/health")
def health(s: Session = Depends(db)) -> dict:
    analyzer = "down"
    try:
        r = httpx.get(f"{ANALYZER_URL}/health", timeout=2)
        analyzer = "ok" if r.status_code == 200 else "down"
    except httpx.HTTPError:
        pass
    last_claim = s.scalar(select(Job.started_at).order_by(Job.started_at.desc()).limit(1))
    return {"api": "ok", "analyzer": analyzer, "websocket_clients": len(hub.clients),
            "last_worker_activity": svc.iso(last_claim), "database": "postgresql" if "postgres" in config.DATABASE_URL else "sqlite"}


@public.get("/stats")
def stats(days: int = Query(30, ge=1, le=365), s: Session = Depends(db)) -> dict:
    return svc.compute_stats(s, days)


@public.get("/findings")
def list_findings(
    module: str | None = None, level: str | None = None, status: str | None = None, platform: str | None = None,
    q: str | None = None, date_from: str | None = None, date_to: str | None = None,
    include_below_threshold: bool = False, sort: Literal["score", "date"] = "score",
    limit: int = Query(200, le=1000), offset: int = 0, s: Session = Depends(db),
) -> dict:
    thresholds = svc.get_thresholds(s)
    stmt = select(Finding).join(Document)
    if module:
        stmt = stmt.where(Finding.module.in_(module.split(",")))
    if level:
        stmt = stmt.where(Finding.level.in_(level.split(",")))
    if status:
        stmt = stmt.where(Finding.status.in_(status.split(",")))
    if platform:
        stmt = stmt.where(Document.platform.in_(platform.split(",")))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Finding.summary.ilike(like), Finding.entity.ilike(like), Finding.firm.ilike(like),
                              Document.url.ilike(like), Document.text.ilike(like)))
    rows = s.scalars(stmt).all()
    lo, hi = svc._parse_dt(date_from), svc._parse_dt(date_to)
    out = []
    for f in rows:
        if not include_below_threshold and f.score < thresholds[f.module]:
            continue
        when = svc.as_utc(f.document.published_at) or svc.as_utc(f.document.first_seen)
        if lo and when < lo:
            continue
        if hi and when >= hi + timedelta(days=1):
            continue
        out.append(f)
    out.sort(key=(lambda f: -f.score) if sort == "score"
             else (lambda f: -(svc.as_utc(f.document.published_at) or svc.as_utc(f.document.first_seen)).timestamp()))
    platforms = sorted({p for (p,) in s.execute(select(Document.platform).distinct())})
    return {"total": len(out), "items": [svc.finding_dict(f, thresholds) for f in out[offset: offset + limit]],
            "thresholds": thresholds, "platforms": platforms}


@public.get("/findings/{finding_id}")
def get_finding(finding_id: int, s: Session = Depends(db)) -> dict:
    f = s.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Nie znaleziono wyniku")
    out = svc.finding_dict(f, svc.get_thresholds(s), detail=True)
    out["related"] = [
        {"id": o.id, "module": o.module, "score": o.score, "summary": o.summary}
        for o in f.document.findings if o.id != f.id
    ]
    return out


class StatusIn(BaseModel):
    status: Literal["new", "in_review", "escalated", "closed", "false_positive"]


STATUS_PL = {"new": "Nowy", "in_review": "W weryfikacji", "escalated": "Eskalowany", "closed": "Zamknięty",
             "false_positive": "Fałszywy alarm"}


@public.patch("/findings/{finding_id}")
def update_finding(finding_id: int, body: StatusIn, s: Session = Depends(db)) -> dict:
    f = s.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Nie znaleziono wyniku")
    old = f.status
    f.status = body.status
    f.updated_at = utcnow()
    svc.log_activity(s, "analyst", f"Status #{f.id} ({f.entity or f.document.url}): {STATUS_PL[old]} → {STATUS_PL[body.status]}")
    s.flush()
    payload = svc.finding_dict(f, svc.get_thresholds(s))
    hub.publish("finding", payload)
    return payload


@public.get("/documents/{doc_id}/raw")
def raw_document(doc_id: int, s: Session = Depends(db)) -> Response:
    d = s.get(Document, doc_id)
    if not d or not d.raw_key or (raw := svc.read_raw(d.raw_key)) is None:
        raise HTTPException(404, "Brak zapisanej kopii")
    # Served as plain text on purpose: scraped HTML must never execute in our origin.
    return Response(raw, media_type="text/plain; charset=utf-8",
                    headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'",
                             "X-Content-SHA256": d.raw_key.split("/")[-1].split(".")[0]})


# --------------------------------------------------------------------- settings / calibration

@public.get("/settings")
def get_settings(s: Session = Depends(db)) -> dict:
    return {"thresholds": svc.get_thresholds(s), "sweep_interval_minutes": config.SWEEP_INTERVAL_MINUTES,
            "register_interval_hours": config.REGISTER_INTERVAL_HOURS, "llm": bool(os.getenv("OLLAMA_URL"))}


class ThresholdsIn(BaseModel):
    m1: float | None = Field(default=None, ge=0, le=100)
    m2: float | None = Field(default=None, ge=0, le=100)
    m3: float | None = Field(default=None, ge=0, le=100)


@public.put("/settings/thresholds")
def put_thresholds(body: ThresholdsIn, s: Session = Depends(db)) -> dict:
    values = {k: v for k, v in body.model_dump().items() if v is not None}
    new = svc.set_thresholds(s, values)
    svc.log_activity(s, "analyst", "Zmieniono progi alertów: " + ", ".join(f"{k.upper()} = {v:.0f}" for k, v in values.items()))
    hub.publish("settings", {"thresholds": new})
    return {"thresholds": new}


@public.get("/calibration")
def get_calibration(module: Literal["m1", "m2", "m3"] = "m2", s: Session = Depends(db)) -> dict:
    return svc.calibration(s, module)


# --------------------------------------------------------------------- sources / jobs

@public.get("/sources")
def list_sources(s: Session = Depends(db)) -> list[dict]:
    return [svc.source_dict(s, x) for x in s.scalars(select(Source).order_by(Source.group, Source.id)).all()]


class SourceIn(BaseModel):
    url: HttpUrl
    kind: Literal["html", "social", "meta_ads", "knf_register"] = "html"
    name: str | None = None


def _check_public_host(url: str) -> None:
    """SSRF guard for user-supplied URLs: block private / loopback targets except the demo corpus."""
    from ipaddress import ip_address
    from urllib.parse import urlparse

    if url.startswith(config.DEMO_SITE_URL):
        return
    host = urlparse(url).hostname or ""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise HTTPException(422, "Nie można rozwiązać nazwy hosta")
    for info in infos:
        ip = ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(422, "Adres wskazuje na sieć wewnętrzną — niedozwolony")


@public.post("/sources")
def create_source(body: SourceIn, s: Session = Depends(db)) -> dict:
    url = str(body.url)
    _check_public_host(url)
    src = s.scalar(select(Source).where(Source.url == url))
    if src is None:
        src = Source(url=url, kind=body.kind, name=body.name or url, group="web")
        s.add(src)
        s.flush()
        svc.log_activity(s, "analyst", f"Dodano źródło: {src.name}")
    job = svc.enqueue(s, src, "manual", priority=5)
    out = svc.source_dict(s, src)
    hub.publish("source", out)
    return {"source": out, "job": svc.job_dict(job) if job else None}


class CheckIn(BaseModel):
    url: HttpUrl


@public.post("/check")
async def check_now(body: CheckIn) -> dict:
    """Fetch and analyse one link right now: queued with top priority, waits for the worker (max ~60 s)."""
    import asyncio

    url = str(body.url)
    await run_in_threadpool(_check_public_host, url)

    def _enqueue() -> tuple[int, int | None]:
        with SessionLocal() as s:
            src = s.scalar(select(Source).where(Source.url == url))
            if src is None:
                src = Source(url=url, kind="html", name=url, group="web")
                s.add(src)
                s.flush()
                svc.log_activity(s, "analyst", f"Sprawdzenie linku: {url}")
            job = svc.enqueue(s, src, "manual", priority=20)
            if job is None:  # already queued / running — wait for that one
                job = s.scalar(select(Job).where(Job.url == url, Job.status.in_(("queued", "running"))))
            s.commit()
            hub.publish("source", svc.source_dict(s, src))
            return src.id, job.id if job else None

    source_id, job_id = await run_in_threadpool(_enqueue)

    def _state() -> dict | None:
        with SessionLocal() as s:
            job = s.get(Job, job_id)
            if job is None or job.status in ("queued", "running"):
                return None
            thresholds = svc.get_thresholds(s)
            docs = s.scalars(select(Document).where(Document.source_id == source_id).order_by(Document.last_seen.desc())).all()
            # Only what this run saw (a link can redirect to a different final URL between runs).
            started = svc.as_utc(job.started_at)
            docs = [d for d in docs if started is None or svc.as_utc(d.last_seen) >= started] or docs[:1]
            return {
                "status": job.status, "error": job.error, "duration_ms": job.duration_ms,
                "documents": [{"id": d.id, "url": d.url, "title": d.title, "author": d.author, "platform": d.platform,
                               "excerpt": d.excerpt} for d in docs],
                "findings": [svc.finding_dict(f, thresholds) for d in docs for f in d.findings],
            }

    for _ in range(120):
        state = await run_in_threadpool(_state)
        if state is not None:
            return state
        await asyncio.sleep(0.5)
    return {"status": "timeout", "error": "Analiza trwa dłużej niż zwykle — wynik pojawi się w Rejestrze alertów.",
            "documents": [], "findings": []}


class SourcePatch(BaseModel):
    active: bool


@public.patch("/sources/{source_id}")
def patch_source(source_id: int, body: SourcePatch, s: Session = Depends(db)) -> dict:
    src = s.get(Source, source_id)
    if not src:
        raise HTTPException(404, "Nie znaleziono źródła")
    src.active = body.active
    out = svc.source_dict(s, src)
    hub.publish("source", out)
    return out


@public.post("/sources/{source_id}/run")
def run_source(source_id: int, s: Session = Depends(db)) -> dict:
    src = s.get(Source, source_id)
    if not src:
        raise HTTPException(404, "Nie znaleziono źródła")
    job = svc.enqueue(s, src, "manual", priority=5)
    return {"job": svc.job_dict(job) if job else None, "already_queued": job is None}


@public.post("/sweep")
def run_sweep(s: Session = Depends(db)) -> dict:
    return {"queued": svc.sweep(s, "manual")}


@public.get("/jobs")
def list_jobs(limit: int = Query(60, le=500), s: Session = Depends(db)) -> list[dict]:
    return [svc.job_dict(j) for j in s.scalars(select(Job).order_by(Job.id.desc()).limit(limit)).all()]


@public.get("/activity")
def list_activity(limit: int = Query(30, le=200), s: Session = Depends(db)) -> list[dict]:
    return [{"id": a.id, "ts": svc.iso(a.ts), "kind": a.kind, "message": a.message}
            for a in s.scalars(select(Activity).order_by(Activity.id.desc()).limit(limit)).all()]


@public.post("/admin/reset")
def reset(s: Session = Depends(db)) -> dict:
    svc.reset_results(s)
    queued = svc.sweep(s, "manual")
    hub.publish("reset", {"queued": queued})
    return {"queued": queued}


# --------------------------------------------------------------------- register

@public.get("/register")
def list_register(q: str | None = None, category: str | None = None, limit: int = Query(100, le=1000),
                  s: Session = Depends(db)) -> dict:
    stmt = select(RegisterEntity)
    if q:
        stmt = stmt.where(RegisterEntity.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(RegisterEntity.category == category)
    rows = s.scalars(stmt.order_by(RegisterEntity.name).limit(limit)).all()
    return {"summary": svc.register_summary(s), "items": [
        {"id": r.id, "name": r.name, "category": r.category, "address": r.address, "license_date": r.license_date,
         "scope": r.scope, "source_url": r.source_url, "fetched_at": svc.iso(r.fetched_at)} for r in rows]}


# --------------------------------------------------------------------- ad-hoc analysis

class AnalyzeIn(BaseModel):
    text: str | None = Field(default=None, max_length=50_000)
    html: str | None = Field(default=None, max_length=500_000)
    url: str = "about:pasted"
    author: str | None = Field(default=None, max_length=300)


@public.post("/analyze")
async def analyze_adhoc(body: AnalyzeIn) -> dict:
    if not body.text and not body.html:
        raise HTTPException(422, "Podaj tekst lub HTML do analizy")
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.post(f"{ANALYZER_URL}/analyze", json=body.model_dump())
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"Silnik analizy niedostępny: {exc}") from exc
    return r.json()


@public.get("/rules")
async def rules() -> list[dict]:
    async with httpx.AsyncClient(timeout=5) as c:
        try:
            return (await c.get(f"{ANALYZER_URL}/rules")).json()
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Silnik analizy niedostępny") from exc


# --------------------------------------------------------------------- reports

REPORT_COLUMNS = {
    "m1": ["Firma inwestycyjna", "Kategoria w rejestrze", "Podmiot reklamujący", "Platforma", "Treść reklamy", "URL",
           "Data publikacji", "Pierwsze wykrycie", "Ostatnia aktualizacja", "Ocena", "Status"],
    "m2": ["Firma", "Naruszone kryteria", "Podstawa prawna", "URL", "Data publikacji", "Ocena", "Status"],
    "m3": ["Podmiot", "Status w rejestrze", "Treść oferty", "Sygnały", "URL", "Data publikacji", "Ocena", "Status"],
}


@public.get("/reports/{module}.csv")
def report_csv(module: Literal["m1", "m2", "m3"], s: Session = Depends(db)) -> Response:
    thresholds = svc.get_thresholds(s)
    rows = [f for f in s.scalars(select(Finding).join(Document).where(Finding.module == module)).all()
            if f.score >= thresholds[module]]
    rows.sort(key=lambda f: -f.score)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(REPORT_COLUMNS[module])
    for f in rows:
        d = f.document
        base_dates = [svc.iso(d.published_at) or "", svc.iso(d.first_seen) or ""]
        if module == "m1":
            w.writerow([f.firm, f.firm_category, f.entity, d.platform, d.excerpt, d.url, *base_dates, svc.iso(d.last_seen),
                        f"{f.score:.0f}", STATUS_PL[f.status]])
        elif module == "m2":
            failed = [r for r in f.rules if r["status"] == "fail"]
            w.writerow([f.entity, "; ".join(r["name"] for r in failed), "; ".join(sorted({r["legal_basis"] for r in failed})),
                        d.url, base_dates[0], f"{f.score:.0f}", STATUS_PL[f.status]])
        else:
            w.writerow([f.entity, "w rejestrze" if f.firm else "brak w rejestrze", d.excerpt,
                        "; ".join(x["label"] for x in f.signals if x.get("weight", 0) > 0), d.url, base_dates[0],
                        f"{f.score:.0f}", STATUS_PL[f.status]])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="investwatch-{module}-raport.csv"'})


# ====================================================================== internal (worker / analyzer)

@internal.get("/jobs/claim", dependencies=[Depends(require_internal)], response_model=None)
async def claim(worker: str = "worker", wait: float = Query(20, ge=0, le=55)) -> Response | dict:
    def _try() -> dict | None:
        with SessionLocal() as s:
            j = svc.claim_job(s, worker)
            return svc.job_dict(j) if j else None

    job = await run_in_threadpool(_try)
    if job is None and wait > 0:
        await svc.queue_signal.wait(wait)
        job = await run_in_threadpool(_try)
    if job is None:
        return Response(status_code=204)
    return job


class ResultIn(BaseModel):
    items: list[dict] = []
    entities: list[dict] | None = None
    category: str | None = None
    error: str | None = None
    fetch: dict = {}


@internal.post("/jobs/{job_id}/result", dependencies=[Depends(require_internal)])
def job_result(job_id: int, body: ResultIn, s: Session = Depends(db)) -> dict:
    job = s.get(Job, job_id)
    if not job:
        raise HTTPException(404, "unknown job")
    job.meta = {**(job.meta or {}), **body.fetch}
    if body.error:
        svc.finish_job(s, job, ok=False, error=body.error[:2000])
        svc.log_activity(s, "system", f"Błąd skanowania {job.url}: {body.error[:160]}")
        return {"ok": False}
    if body.entities is not None:
        n = svc.replace_register(s, job.url, body.category or "dom_maklerski", body.entities)
        svc.finish_job(s, job, ok=True, count=n)
        svc.log_activity(s, "sweep", f"Zaktualizowano rejestr UKNF: {n} podmiotów ({body.category})")
        hub.publish("register", svc.register_summary(s))
        return {"ok": True, "entities": n}
    alerts = svc.ingest_items(s, job, body.items)
    svc.finish_job(s, job, ok=True, count=len(body.items))
    return {"ok": True, "alerts": alerts}


@internal.get("/register", dependencies=[Depends(require_internal)])
def internal_register(s: Session = Depends(db)) -> list[dict]:
    return [{"name": r.name, "category": r.category, "scope": r.scope, "source_url": r.source_url}
            for r in s.scalars(select(RegisterEntity)).all()]
