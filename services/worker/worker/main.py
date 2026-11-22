"""Scraper worker: claims jobs from the API queue, collects, analyzes, reports back."""

from __future__ import annotations

import logging
import os
import signal
import socket
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from urllib.parse import quote

from .collectors import (COLLECTORS, collect_knf_register, collect_tiktok_oembed, collect_youtube, next_page_url,
                         platform_of, register_category)
from .fetcher import FetchError, Fetcher

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("worker")

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8001").rstrip("/")
TOKEN = os.getenv("INTERNAL_TOKEN", "dev-internal-token")
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "3"))
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"

running = True
fetcher = Fetcher()
api = httpx.Client(base_url=API_URL, headers={"X-Internal-Token": TOKEN}, timeout=httpx.Timeout(70, connect=5))
analyzer = httpx.Client(base_url=ANALYZER_URL, timeout=60)


def report(job_id: int, payload: dict) -> None:
    for attempt in range(3):
        try:
            api.post(f"/internal/jobs/{job_id}/result", json=payload).raise_for_status()
            return
        except httpx.HTTPError as exc:
            log.warning("report job %s failed (%s), retrying", job_id, exc)
            time.sleep(1 + attempt)


def process(job: dict) -> None:
    t0 = time.perf_counter()
    url, kind = job["url"], job["kind"]
    try:
        platform = platform_of(url) if kind in ("html", "social") else None
        if platform == "www" and kind == "social":
            platform = None
        if platform == "tiktok" and "/video/" in url:
            # Official public oEmbed endpoint instead of the JavaScript-only video page.
            res = fetcher.get(f"https://www.tiktok.com/oembed?url={quote(url, safe='')}")
        else:
            res = fetcher.get(url)
        fetch_meta = {"status": res.status, "final_url": res.final_url, "user_agent": res.user_agent,
                      "proxy": res.proxy, "attempts": res.attempts, "fetch_ms": res.elapsed_ms, "bytes": len(res.text)}
        if kind == "knf_register":
            entities, visited, page = collect_knf_register(res), {res.final_url}, res
            while (nxt := next_page_url(page, visited)) and len(visited) < 30:
                page = fetcher.get(nxt)
                visited.add(nxt)
                entities += collect_knf_register(page)
            fetch_meta["pages"] = len(visited)
            if not entities:
                raise ValueError("Nie znaleziono podmiotów — zmieniła się struktura strony rejestru")
            report(job["id"], {"entities": entities, "category": register_category(url), "fetch": fetch_meta})
            log.info("job %s register %s: %d entities", job["id"], url, len(entities))
            return
        if platform == "tiktok" and "/video/" in url:
            items = collect_tiktok_oembed(res, url)
        elif platform == "tiktok":
            raise ValueError("TikTok udostępnia treść tylko w aplikacji lub po zalogowaniu — wklej opis ręcznie")
        elif platform == "youtube":
            items = collect_youtube(res)
        else:
            items = COLLECTORS[kind](res)
        out = []
        for it in items:
            r = analyzer.post("/analyze", json={"url": it.url, "html": it.html, "text": it.text, "author": it.author, "title": it.title})
            r.raise_for_status()
            out.append({"url": it.url, "platform": it.platform, "published_at": it.published_at, "raw": it.raw,
                        "raw_type": it.raw_type, "analysis": r.json()})
        report(job["id"], {"items": out, "fetch": fetch_meta})
        log.info("job %s %s: %d item(s) in %.0f ms", job["id"], url, len(out), (time.perf_counter() - t0) * 1000)
    except (FetchError, ValueError, KeyError, httpx.HTTPError) as exc:
        log.warning("job %s %s failed: %s", job["id"], url, exc)
        report(job["id"], {"error": str(exc)})
    except Exception as exc:  # noqa: BLE001 — never let one bad page kill the worker
        log.exception("job %s crashed", job["id"])
        report(job["id"], {"error": f"Błąd wewnętrzny: {exc}"})


def claim() -> dict | None:
    try:
        r = api.get("/internal/jobs/claim", params={"worker": WORKER_ID, "wait": 25})
        if r.status_code == 204:
            return None
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as exc:
        log.warning("API unavailable (%s) — retrying in 3 s", exc)
        time.sleep(3)
        return None


def loop(slot: int) -> None:
    while running:
        job = claim()
        if job:
            process(job)


def main() -> None:
    def stop(*_):
        global running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("worker %s started (concurrency=%d, api=%s)", WORKER_ID, CONCURRENCY, API_URL)
    with ThreadPoolExecutor(CONCURRENCY) as pool:
        for i in range(CONCURRENCY):
            pool.submit(loop, i)


if __name__ == "__main__":
    main()
