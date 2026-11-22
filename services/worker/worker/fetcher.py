"""Polite HTTP fetcher: User-Agent + proxy rotation, retries, robots.txt, per-host rate limit."""

from __future__ import annotations

import itertools
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger("worker.fetch")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36",
]
ROBOTS_AGENT = "InvestWatchBot"
MAX_BYTES = int(os.getenv("FETCH_MAX_BYTES", str(5 * 1024 * 1024)))
MIN_INTERVAL = float(os.getenv("FETCH_MIN_INTERVAL_SECONDS", "1.0"))
RESPECT_ROBOTS = os.getenv("RESPECT_ROBOTS", "true").lower() != "false"
PROXIES = [p.strip() for p in os.getenv("PROXIES", "").split(",") if p.strip()]
# "public=internal" pairs, e.g. http://localhost:8080=http://demo-sites — lets containers fetch
# the demo corpus by its internal name while the UI keeps host-reachable links.
URL_REWRITE = [tuple(p.split("=", 1)) for p in os.getenv("URL_REWRITE", "").split(",") if "=" in p]


def rewrite(url: str) -> str:
    for public, internal in URL_REWRITE:
        if url.startswith(public):
            return internal + url[len(public):]
    return url


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    content_type: str
    text: str
    user_agent: str
    proxy: str | None
    attempts: int
    elapsed_ms: int


class FetchError(Exception):
    pass


class Fetcher:
    def __init__(self) -> None:
        self._ua = itertools.cycle(random.sample(USER_AGENTS, len(USER_AGENTS)))
        self._proxy = itertools.cycle(PROXIES) if PROXIES else None
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}
        self._lock = threading.Lock()

    def _throttle(self, host: str) -> None:
        with self._lock:
            wait = self._last_hit.get(host, 0) + MIN_INTERVAL - time.monotonic()
            self._last_hit[host] = time.monotonic() + max(0, wait)
        if wait > 0:
            time.sleep(wait)

    def allowed(self, url: str) -> bool:
        if not RESPECT_ROBOTS:
            return True
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = RobotFileParser()
            try:
                r = httpx.get(base + "/robots.txt", timeout=10, headers={"User-Agent": USER_AGENTS[0]}, follow_redirects=True)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                self._robots[base] = rp
            except httpx.HTTPError:
                self._robots[base] = None  # unreachable robots.txt -> allow
        rp = self._robots[base]
        return rp is None or rp.can_fetch(ROBOTS_AGENT, url)

    def get(self, url: str, retries: int = 3) -> FetchResult:
        public_url, url = url, rewrite(url)
        if not self.allowed(url):
            raise FetchError(f"Serwis {urlparse(url).hostname} nie zezwala na automatyczne pobieranie (robots.txt) — wklej treść ręcznie")
        host = urlparse(url).netloc
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            ua = next(self._ua)
            proxy = next(self._proxy) if self._proxy else None
            self._throttle(host)
            t0 = time.perf_counter()
            try:
                with httpx.Client(proxy=proxy, timeout=httpx.Timeout(20, connect=10), follow_redirects=True,
                                  headers={"User-Agent": ua, "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.6",
                                           "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}) as c:
                    with c.stream("GET", url) as r:
                        if r.status_code in (429, 500, 502, 503, 504):
                            raise FetchError(f"HTTP {r.status_code}")
                        if r.status_code in (401, 403):
                            raise FetchError(f"HTTP {r.status_code} — serwis odmówił dostępu (wymaga logowania lub blokuje automaty)")
                        if r.status_code == 404:
                            raise FetchError("HTTP 404 — strona nie istnieje")
                        if r.status_code >= 400:
                            raise FetchError(f"HTTP {r.status_code}")  # not retried below
                        body = b""
                        for chunk in r.iter_bytes():
                            body += chunk
                            if len(body) > MAX_BYTES:
                                raise FetchError("Przekroczono maksymalny rozmiar strony")
                        text = body.decode(r.encoding or "utf-8", errors="replace")
                        final = str(r.url) if url == public_url else public_url
                        return FetchResult(public_url, final, r.status_code, r.headers.get("content-type", ""), text, ua,
                                           proxy, attempt, int((time.perf_counter() - t0) * 1000))
            except (httpx.HTTPError, FetchError) as exc:
                last_exc = exc
                permanent = isinstance(exc, FetchError) and exc.args and str(exc.args[0]).startswith("HTTP 4") and "429" not in str(exc)
                log.warning("fetch %s attempt %d failed: %s", url, attempt, exc)
                if permanent or attempt == retries:
                    break
                time.sleep(min(8.0, 0.8 * 2 ** attempt) + random.random() * 0.5)
        raise FetchError(str(last_exc) if last_exc else "Nieznany błąd pobierania")
