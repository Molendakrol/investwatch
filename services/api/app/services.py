"""Business logic shared by the HTTP routes and the scheduler."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from . import config
from .db import Activity, Document, Finding, GoldLabel, Job, RegisterEntity, Setting, Source, utcnow
from .events import hub

log = logging.getLogger("api")

MODULES = ("m1", "m2", "m3")
OPEN_STATUSES = ("new", "in_review", "escalated")


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt: datetime | None) -> str | None:
    dt = as_utc(dt)
    return dt.isoformat() if dt else None


# ------------------------------------------------------------------ activity / settings

def log_activity(s: Session, kind: str, message: str) -> None:
    a = Activity(kind=kind, message=message)
    s.add(a)
    s.flush()
    hub.publish("activity", {"id": a.id, "ts": iso(a.ts), "kind": kind, "message": message})


def get_thresholds(s: Session) -> dict[str, float]:
    row = s.get(Setting, "thresholds")
    values = dict(row.value) if row else {}
    return {m: float(values.get(m, config.DEFAULT_THRESHOLD)) for m in MODULES}


def set_thresholds(s: Session, values: dict[str, float]) -> dict[str, float]:
    current = get_thresholds(s)
    current.update({k: max(0.0, min(100.0, float(v))) for k, v in values.items() if k in MODULES})
    row = s.get(Setting, "thresholds")
    if row:
        row.value = current
    else:
        s.add(Setting(key="thresholds", value=current))
    return current


def get_setting(s: Session, key: str) -> dict[str, Any]:
    row = s.get(Setting, key)
    return dict(row.value) if row else {}


def put_setting(s: Session, key: str, value: dict[str, Any]) -> None:
    row = s.get(Setting, key)
    if row:
        row.value = value
    else:
        s.add(Setting(key=key, value=value))


# ------------------------------------------------------------------ job queue

class QueueSignal:
    """Wakes long-polling workers as soon as a job is enqueued."""

    def __init__(self) -> None:
        self.cond: asyncio.Condition | None = None

    def bind(self) -> None:
        self.cond = asyncio.Condition()

    async def _notify(self) -> None:
        assert self.cond
        async with self.cond:
            self.cond.notify_all()

    def notify(self) -> None:
        if hub.loop and self.cond:
            asyncio.run_coroutine_threadsafe(self._notify(), hub.loop)

    async def wait(self, timeout: float) -> None:
        assert self.cond
        async with self.cond:
            try:
                await asyncio.wait_for(self.cond.wait(), timeout)
            except asyncio.TimeoutError:
                pass


queue_signal = QueueSignal()


def job_dict(j: Job) -> dict:
    return {
        "id": j.id, "source_id": j.source_id, "url": j.url, "kind": j.kind, "status": j.status, "trigger": j.trigger,
        "attempts": j.attempts, "worker": j.worker, "created_at": iso(j.created_at), "started_at": iso(j.started_at),
        "finished_at": iso(j.finished_at), "duration_ms": j.duration_ms, "result_count": j.result_count, "error": j.error,
    }


def enqueue(s: Session, source: Source, trigger: str = "manual", priority: int = 0) -> Job | None:
    existing = s.scalar(select(Job).where(Job.url == source.url, Job.status.in_(("queued", "running"))))
    if existing:
        return None
    job = Job(source_id=source.id, url=source.url, kind=source.kind, trigger=trigger, priority=priority)
    s.add(job)
    s.flush()
    hub.publish("job", job_dict(job))
    queue_signal.notify()
    return job


def claim_job(s: Session, worker: str) -> Job | None:
    """Atomic claim: works on SQLite and PostgreSQL (conditional UPDATE, retry on race)."""
    for _ in range(5):
        cand = s.scalar(select(Job.id).where(Job.status == "queued").order_by(Job.priority.desc(), Job.id).limit(1))
        if cand is None:
            return None
        res = s.execute(
            update(Job).where(Job.id == cand, Job.status == "queued")
            .values(status="running", worker=worker, started_at=utcnow(), attempts=Job.attempts + 1)
        )
        s.commit()
        if res.rowcount == 1:
            job = s.get(Job, cand)
            hub.publish("job", job_dict(job))
            return job
    return None


def finish_job(s: Session, job: Job, *, ok: bool, count: int = 0, error: str | None = None) -> None:
    job.status = "done" if ok else "failed"
    job.finished_at = utcnow()
    started = as_utc(job.started_at)
    job.duration_ms = int((job.finished_at - started).total_seconds() * 1000) if started else None
    job.result_count = count
    job.error = error
    if job.source_id and (src := s.get(Source, job.source_id)):
        src.last_run_at = job.finished_at
        src.last_status = job.status
        src.last_error = error
        if ok:
            src.items_found = count
        hub.publish("source", source_dict(s, src))
    hub.publish("job", job_dict(job))


def requeue_stale(s: Session, older_than: timedelta = timedelta(minutes=3)) -> int:
    limit = utcnow() - older_than
    stale = s.scalars(select(Job).where(Job.status == "running", Job.started_at < limit)).all()
    for j in stale:
        if j.attempts >= 3:
            j.status, j.error, j.finished_at = "failed", "Przekroczono limit prób (worker nie odpowiedział).", utcnow()
        else:
            j.status = "queued"
        hub.publish("job", job_dict(j))
    if stale:
        queue_signal.notify()
    return len(stale)


# ------------------------------------------------------------------ sources

def source_dict(s: Session, src: Source) -> dict:
    return {
        "id": src.id, "url": src.url, "kind": src.kind, "name": src.name, "group": src.group, "active": src.active,
        "created_at": iso(src.created_at), "last_run_at": iso(src.last_run_at), "last_status": src.last_status,
        "last_error": src.last_error, "items_found": src.items_found,
    }


def sweep(s: Session, trigger: str, groups: tuple[str, ...] | None = None) -> int:
    q = select(Source).where(Source.active.is_(True))
    if groups:
        q = q.where(Source.group.in_(groups))
    n = 0
    for src in s.scalars(q.order_by(Source.group.desc(), Source.id)).all():
        priority = 10 if src.kind == "knf_register" else 0
        if enqueue(s, src, trigger, priority):
            n += 1
    if n:
        log_activity(s, "sweep", f"Zaplanowano skanowanie {n} źródeł ({'harmonogram' if trigger == 'schedule' else 'ręcznie'})")
    return n


# ------------------------------------------------------------------ object store

def store_raw(raw: str, raw_type: str) -> str:
    digest = hashlib.sha256(raw.encode()).hexdigest()
    key = f"{digest[:2]}/{digest}.{ 'json' if raw_type == 'json' else 'html' if raw_type == 'html' else 'txt'}"
    path = config.OBJECT_STORE_DIR / key
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
    return key


def read_raw(key: str) -> str | None:
    path = (config.OBJECT_STORE_DIR / key).resolve()
    if config.OBJECT_STORE_DIR.resolve() not in path.parents or not path.exists():
        return None
    return path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ findings

def finding_dict(f: Finding, thresholds: dict[str, float], detail: bool = False) -> dict:
    d = f.document
    out = {
        "id": f.id, "module": f.module, "score": f.score, "level": f.level, "status": f.status, "summary": f.summary,
        "entity": f.entity, "firm": f.firm, "firm_category": f.firm_category, "is_alert": f.score >= thresholds[f.module],
        "created_at": iso(f.created_at), "updated_at": iso(f.updated_at),
        "document": {
            "id": d.id, "url": d.url, "platform": d.platform, "title": d.title, "author": d.author,
            "site_name": d.site_name, "published_at": iso(d.published_at), "first_seen": iso(d.first_seen),
            "last_seen": iso(d.last_seen), "excerpt": d.excerpt, "scan_count": d.scan_count,
            "change_count": d.change_count, "duplicate_of": d.duplicate_of,
        },
        "top_signals": [x.get("label") for x in (f.signals or []) if x.get("weight", 0) > 0][:3]
        or [r.get("name") for r in (f.rules or []) if r.get("status") == "fail"][:3],
    }
    if detail:
        out["signals"] = f.signals
        out["rules"] = f.rules
        out["document"]["text"] = d.text
        out["document"]["content_hash"] = d.content_hash
        out["document"]["has_raw"] = bool(d.raw_key)
    return out


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def ingest_items(s: Session, job: Job, items: list[dict]) -> int:
    thresholds = get_thresholds(s)
    known = s.scalars(select(Document)).all()
    count = 0
    for item in items:
        analysis = item["analysis"]
        meta = analysis["document"]
        url = item["url"]
        raw_key = store_raw(item["raw"], item.get("raw_type", "html")) if item.get("raw") else None
        doc = s.scalar(select(Document).where(Document.url == url))
        now = utcnow()
        if doc is None:
            doc = Document(url=url, source_id=job.source_id, first_seen=now, last_seen=now, scan_count=1,
                           content_hash=meta["content_hash"], simhash=meta["simhash"])
            s.add(doc)
            sim = int(meta["simhash"])
            for other in known:
                if other.url != url and bin(int(other.simhash) ^ sim).count("1") <= 3:
                    doc.duplicate_of = other.id
                    break
        else:
            doc.last_seen = now
            doc.scan_count += 1
            if doc.content_hash != meta["content_hash"]:
                doc.change_count += 1
                log_activity(s, "system", f"Zmieniła się treść materiału: {url}")
        doc.platform = item.get("platform") or doc.platform
        doc.title = (meta.get("title") or "")[:500]
        doc.author = meta.get("author")
        doc.site_name = meta.get("site_name")
        doc.published_at = _parse_dt(item.get("published_at")) or doc.published_at
        doc.content_hash, doc.simhash = meta["content_hash"], meta["simhash"]
        doc.text, doc.excerpt = meta.get("text", ""), meta.get("excerpt", "")
        doc.raw_key = raw_key or doc.raw_key
        s.flush()

        for a in analysis["assessments"]:
            f = s.scalar(select(Finding).where(Finding.document_id == doc.id, Finding.module == a["module"]))
            is_new = f is None
            if is_new:
                f = Finding(document_id=doc.id, module=a["module"])
                s.add(f)
            was_alert = (not is_new) and f.score >= thresholds[a["module"]]
            f.score, f.level, f.summary = a["score"], a["level"], a["summary"]
            f.entity, f.firm, f.firm_category = a.get("entity"), a.get("firm"), a.get("firm_category")
            f.signals, f.rules, f.updated_at = a.get("signals", []), a.get("rules", []), now
            s.flush()
            s.refresh(f)
            is_alert = f.score >= thresholds[f.module]
            payload = finding_dict(f, thresholds)
            hub.publish("finding", payload)
            if is_alert and not was_alert:
                count += 1
                log_activity(s, "flag", f"[{f.module.upper()}] {f.summary} — ocena {f.score:.0f}")
                hub.publish("alert", payload)
    return count


# ------------------------------------------------------------------ register

def replace_register(s: Session, source_url: str, category: str, entities: list[dict]) -> int:
    s.execute(delete(RegisterEntity).where(RegisterEntity.source_url == source_url))
    seen: set[str] = set()
    for e in entities:
        name = (e.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        s.add(RegisterEntity(name=name[:400], category=category, address=e.get("address", "")[:2000],
                             license_date=e.get("license_date", "")[:40], scope=e.get("scope", "")[:300], source_url=source_url))
    return len(seen)


def register_summary(s: Session) -> dict:
    rows = s.execute(select(RegisterEntity.category, func.count(), func.max(RegisterEntity.fetched_at))
                     .group_by(RegisterEntity.category)).all()
    return {"total": sum(r[1] for r in rows),
            "by_category": {r[0]: r[1] for r in rows},
            "fetched_at": iso(max((as_utc(r[2]) for r in rows if r[2]), default=None))}


# ------------------------------------------------------------------ seeding

DEMO_REGISTER = [
    ("Dom Maklerski Nordwisła S.A.", "1, 2, 3, 4, 5, 6"),
    ("Vistula Invest Dom Maklerski S.A.", "1, 4, 5, 6"),
    ("Baltic Capital Markets Ltd", "transgraniczna (UE)"),
    ("Mazowiecki Dom Inwestycyjny S.A.", "1, 4, 6"),
]


def seed(s: Session) -> bool:
    """Idempotent seed. Returns True when the database was empty (first start)."""
    first_start = s.scalar(select(func.count(Source.id))) == 0
    if s.get(Setting, "thresholds") is None:
        set_thresholds(s, {})
    for name, url in config.KNF_REGISTER_SOURCES:
        if not s.scalar(select(Source).where(Source.url == url)):
            s.add(Source(url=url, kind="knf_register", name=name, group="register"))
    if not s.scalar(select(func.count(RegisterEntity.id)).where(RegisterEntity.category == "demo")):
        for name, scope in DEMO_REGISTER:
            s.add(RegisterEntity(name=name, category="demo", scope=scope, source_url="demo",
                                 address="Podmiot fikcyjny — korpus testowy"))
    if config.DEMO_MANIFEST.exists():
        base = config.DEMO_MANIFEST.parent
        for item in json.loads(config.DEMO_MANIFEST.read_text(encoding="utf-8")):
            url = f"{config.DEMO_SITE_URL}/{item['path']}"
            if not s.scalar(select(Source).where(Source.url == url)):
                s.add(Source(url=url, kind=item["kind"], name=f"Korpus testowy — {item['note']}", group="demo"))
            labels: list[tuple[str, str, bool, str]] = []
            if item["kind"] == "html":
                labels.append((url, item["module"], item["label"], item["note"]))
            elif item["kind"] == "social":
                post = json.loads((base / item["path"]).read_text(encoding="utf-8"))
                labels.append((post["url"], item["module"], item["label"], item["note"]))
            else:
                for ad_url, g in item.get("items", {}).items():
                    labels.append((ad_url, g["module"], g["label"], f"Meta Ad Library — {ad_url.rsplit('=', 1)[-1]}"))
            for u, m, lab, note in labels:
                if not s.scalar(select(GoldLabel).where(GoldLabel.url == u, GoldLabel.module == m)):
                    s.add(GoldLabel(url=u, module=m, label=bool(lab), note=note))
    if first_start:
        s.add(Activity(kind="system", message="Uruchomiono InvestWatch — pierwsze skanowanie źródeł"))
    s.commit()
    return first_start


def reset_results(s: Session) -> None:
    s.execute(delete(Finding))
    s.execute(delete(Document))
    s.execute(delete(Job))
    s.execute(delete(Activity))
    s.execute(update(Source).values(last_run_at=None, last_status=None, last_error=None, items_found=0))
    log_activity(s, "system", "Wyczyszczono wyniki — ponowne skanowanie wszystkich źródeł")


# ------------------------------------------------------------------ analytics

def compute_stats(s: Session, days: int) -> dict:
    thresholds = get_thresholds(s)
    now = utcnow()
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    findings = s.scalars(select(Finding).join(Document)).all()
    alerts = [f for f in findings if f.score >= thresholds[f.module]]

    def when(f: Finding) -> datetime:
        return as_utc(f.document.published_at) or as_utc(f.document.first_seen)

    in_range = [f for f in alerts if when(f) >= start]
    buckets = []
    for i in range(days + 1):
        day = (start + timedelta(days=i)).date()
        counts = {lvl: 0 for lvl in ("critical", "high", "medium", "low")}
        for f in in_range:
            if when(f).date() == day:
                counts[f.level] += 1
        buckets.append({"date": day.isoformat(), "counts": counts})

    rule_fail: dict[str, dict] = {}
    signal_hits: dict[str, dict] = {}
    for f in in_range:
        for r in f.rules or []:
            if r.get("status") == "fail":
                e = rule_fail.setdefault(r["id"], {"id": r["id"], "name": r["name"], "legal_basis": r["legal_basis"], "count": 0})
                e["count"] += 1
        for sig in f.signals or []:
            if sig.get("weight", 0) > 0:
                key = f"{f.module}:{sig['code']}"
                e = signal_hits.setdefault(key, {"module": f.module, "code": sig["code"], "label": sig["label"].split(":")[0].split("(")[0].strip(), "count": 0})
                e["count"] += 1

    jobs_24h = s.scalars(select(Job).where(Job.created_at >= now - timedelta(hours=24))).all()
    docs = s.scalar(select(func.count(Document.id))) or 0
    sources = s.scalars(select(Source)).all()
    last_sweep = s.scalar(select(func.max(Job.finished_at)).where(Job.status == "done"))
    return {
        "generated_at": iso(now),
        "days": days,
        "thresholds": thresholds,
        "kpi": {
            "documents": docs,
            "documents_in_range": len({f.document_id for f in findings if when(f) >= start}),
            "alerts": len(in_range),
            "critical": sum(1 for f in in_range if f.level == "critical"),
            "open": sum(1 for f in in_range if f.status in OPEN_STATUSES),
            "escalated": sum(1 for f in in_range if f.status == "escalated"),
            "by_module": {m: sum(1 for f in in_range if f.module == m) for m in MODULES},
            "by_level": {lvl: sum(1 for f in in_range if f.level == lvl) for lvl in ("critical", "high", "medium", "low")},
            "jobs_24h": len(jobs_24h),
            "jobs_failed_24h": sum(1 for j in jobs_24h if j.status == "failed"),
            "queue": s.scalar(select(func.count(Job.id)).where(Job.status.in_(("queued", "running")))) or 0,
        },
        "timeline": buckets,
        "top_rules": sorted(rule_fail.values(), key=lambda x: -x["count"])[:8],
        "top_signals": sorted(signal_hits.values(), key=lambda x: -x["count"])[:8],
        "sources": {
            "total": len(sources), "active": sum(1 for x in sources if x.active),
            "failed": sum(1 for x in sources if x.last_status == "failed"),
            "never_run": sum(1 for x in sources if x.last_status is None),
        },
        "last_sweep": iso(last_sweep),
        "register": register_summary(s),
    }


def calibration(s: Session, module: str) -> dict:
    thresholds = get_thresholds(s)
    labels = s.scalars(select(GoldLabel).where(GoldLabel.module == module)).all()
    items = []
    for g in labels:
        doc = s.scalar(select(Document).where(Document.url == g.url))
        if doc is None:
            continue
        f = next((x for x in doc.findings if x.module == module), None)
        items.append({"url": g.url, "note": g.note, "label": g.label, "score": f.score if f else 0.0,
                      "finding_id": f.id if f else None, "title": doc.title or g.note})
    curve = []
    for t in range(0, 101):
        tp = sum(1 for i in items if i["label"] and i["score"] >= t)
        fp = sum(1 for i in items if not i["label"] and i["score"] >= t)
        fn = sum(1 for i in items if i["label"] and i["score"] < t)
        tn = sum(1 for i in items if not i["label"] and i["score"] < t)
        p = tp / (tp + fp) if tp + fp else 1.0
        r = tp / (tp + fn) if tp + fn else 0.0
        curve.append({"t": t, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(p, 3), "recall": round(r, 3),
                      "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0})
    best = None
    if items:
        top = max(c["f1"] for c in curve)
        plateau = [c["t"] for c in curve if c["f1"] == top]
        # middle of the longest run of optimal thresholds = most robust choice
        runs, run = [], [plateau[0]]
        for t in plateau[1:]:
            if t == run[-1] + 1:
                run.append(t)
            else:
                runs.append(run)
                run = [t]
        runs.append(run)
        longest = max(runs, key=len)
        best = {"t": longest[len(longest) // 2]}
    live = s.scalars(select(Finding).where(Finding.module == module)).all()
    return {"module": module, "threshold": thresholds[module], "items": sorted(items, key=lambda i: -i["score"]),
            "curve": curve, "recommended": best["t"] if best else None, "labelled": len(labels),
            "scores_all": sorted(round(f.score, 1) for f in live)}
