"""InvestWatch API — REST + WebSocket + job queue + scheduler."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from . import config, services as svc
from .db import Job, RegisterEntity, SessionLocal, init_db, utcnow
from .events import hub
from .routes import internal, public

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")


def _scheduler_tick() -> None:
    """Orchestrator: periodic sweeps, daily register refresh, stale job recovery."""
    with SessionLocal() as s:
        svc.requeue_stale(s)
        state = svc.get_setting(s, "scheduler")
        now = utcnow()

        def due(key: str, every: timedelta) -> bool:
            last = state.get(key)
            return last is None or now - datetime.fromisoformat(last) >= every

        if due("last_register", timedelta(hours=config.REGISTER_INTERVAL_HOURS)):
            svc.sweep(s, "schedule", groups=("register",))
            state["last_register"] = now.isoformat()
        if due("last_sweep", timedelta(minutes=config.SWEEP_INTERVAL_MINUTES)):
            svc.sweep(s, "schedule", groups=("demo", "web", "social"))
            state["last_sweep"] = now.isoformat()
        svc.put_setting(s, "scheduler", state)
        s.commit()


async def scheduler_loop() -> None:
    while True:
        try:
            await run_in_threadpool(_scheduler_tick)
        except Exception:  # noqa: BLE001
            log.exception("scheduler tick failed")
        await asyncio.sleep(20)


@asynccontextmanager
async def lifespan(_: FastAPI):
    hub.loop = asyncio.get_running_loop()
    svc.queue_signal.bind()
    init_db()
    with SessionLocal() as s:
        svc.seed(s)
        has_register = (s.scalar(select(func.count(RegisterEntity.id)).where(RegisterEntity.category != "demo")) or 0) > 0
        stuck = s.scalars(select(Job).where(Job.status == "running")).all()
        for j in stuck:
            j.status = "queued"
        if not has_register:
            # first start: fetch the register before scanning content
            state = svc.get_setting(s, "scheduler")
            state.pop("last_register", None)
            svc.put_setting(s, "scheduler", state)
        s.commit()
    task = asyncio.create_task(scheduler_loop())
    log.info("InvestWatch API ready (db=%s)", config.DATABASE_URL.split("://")[0])
    yield
    task.cancel()


app = FastAPI(title="InvestWatch API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(public)
app.include_router(internal)


# Serve the built panel from the API as well (http://localhost:8000) — no separate dev server needed.
_dist = os.getenv("FRONTEND_DIST", str(config.ROOT / "frontend" / "dist"))
if os.path.isdir(_dist):
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def _index():
        from fastapi.responses import FileResponse

        return FileResponse(os.path.join(_dist, "index.html"))

    @app.get("/favicon.svg", include_in_schema=False)
    def _favicon():
        from fastapi.responses import FileResponse

        return FileResponse(os.path.join(_dist, "favicon.svg"))


@app.websocket("/ws")
async def websocket(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        await ws.send_json({"type": "hello", "payload": {"clients": len(hub.clients)}})
        while True:
            await ws.receive_text()  # keep-alive pings from the client
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
