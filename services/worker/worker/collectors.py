"""Collectors turn a fetched resource into items for the analyzer.

html          — any web page (landing pages, blogs, rankings)
social        — single post exported from a platform API (Instagram / TikTok / Facebook / YouTube / Telegram)
meta_ads      — Meta Ad Library API response (`ads_archive` fields: page_name, ad_creative_bodies, ad_snapshot_url…)
knf_register  — UKNF register pages of investment firms (tables Nazwa / Dane teleadresowe / Data zezwolenia / Zakres)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .fetcher import FetchResult


@dataclass
class Item:
    url: str
    platform: str
    raw: str
    raw_type: str  # html | json | text
    html: str | None = None
    text: str | None = None
    author: str | None = None
    title: str = ""
    published_at: str | None = None


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for n in names:
        el = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if el and el.get("content"):
            return el["content"]
    return None


PLATFORMS = {
    "youtube.com": "youtube", "youtu.be": "youtube", "tiktok.com": "tiktok", "instagram.com": "instagram",
    "facebook.com": "facebook", "fb.com": "facebook", "x.com": "x", "twitter.com": "x", "linkedin.com": "linkedin",
    "t.me": "telegram",
}
LOGIN_WALLED = {"instagram", "facebook", "x", "linkedin"}


def platform_of(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").removeprefix("www.").removeprefix("m.")
    return next((p for h, p in PLATFORMS.items() if host == h or host.endswith("." + h)), "www")


def _json_ld_texts(soup: BeautifulSoup) -> tuple[list[str], str | None]:
    texts, author = [], None
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.get_text())
        except ValueError:
            continue
        for obj in data if isinstance(data, list) else [data]:
            if not isinstance(obj, dict):
                continue
            for k in ("headline", "name", "description", "articleBody", "text"):
                if isinstance(obj.get(k), str):
                    texts.append(obj[k])
            a = obj.get("author")
            if isinstance(a, dict) and isinstance(a.get("name"), str):
                author = author or a["name"]
            elif isinstance(a, list) and a and isinstance(a[0], dict):
                author = author or a[0].get("name")
    return texts, author


def collect_youtube(res: FetchResult) -> list[Item]:
    """YouTube watch page: title, channel and full description are embedded in the page JSON."""
    def field(name: str) -> str | None:
        m = re.search(rf'"{name}":"((?:[^"\\]|\\.)*)"', res.text)
        return json.loads(f'"{m.group(1)}"') if m else None

    soup = BeautifulSoup(res.text, "html.parser")
    # The page JSON holds many "title" keys (UI labels); the meta tags hold the video's own title.
    title = _meta(soup, "og:title", "title", "twitter:title") or field("title")
    desc = field("shortDescription")
    if not desc and not title:
        return collect_html(res)
    text = "\n\n".join(x for x in (title, desc) if x)
    return [Item(url=res.final_url, platform="youtube", raw=res.text, raw_type="html", text=text,
                 author=field("ownerChannelName") or field("author"), title=title or "",
                 published_at=field("publishDate") or field("uploadDate"))]


def collect_tiktok_oembed(res: FetchResult, original_url: str) -> list[Item]:
    """TikTok official oEmbed API (public, no login): caption and author of a video."""
    data = json.loads(res.text)
    caption = data.get("title") or ""
    if not caption:
        raise ValueError("TikTok nie udostępnia opisu filmu bez logowania — wklej opis filmu ręcznie")
    return [Item(url=original_url, platform="tiktok", raw=res.text, raw_type="json", text=caption,
                 author=data.get("author_name") or data.get("author_unique_id"), title=caption[:120])]


def collect_html(res: FetchResult) -> list[Item]:
    if "json" in res.content_type:
        raise ValueError("Zasób jest JSON-em — wybierz typ źródła „social” lub „meta_ads”")
    soup = BeautifulSoup(res.text, "html.parser")
    platform = platform_of(res.final_url)
    published = _meta(soup, "article:published_time", "og:published_time", "date", "pubdate")
    if not published and (t := soup.find("time", attrs={"datetime": True})):
        published = t["datetime"]
    visible = soup.body.get_text(" ", strip=True) if soup.body else ""
    if len(visible) < 200:
        # JavaScript-only page: fall back to the metadata it publishes for link previews.
        ld_texts, ld_author = _json_ld_texts(soup)
        parts = [_meta(soup, "og:title") or (soup.title.get_text(strip=True) if soup.title else None),
                 _meta(soup, "og:description", "description", "twitter:description"), *ld_texts]
        text = "\n\n".join(dict.fromkeys(p.strip() for p in parts if p and p.strip()))
        if len(visible) >= 40 and len(text) <= len(visible):
            # A short but ordinary page: its own text is the best source.
            return [Item(url=res.final_url, platform=platform, raw=res.text, raw_type="html", html=res.text,
                         published_at=published)]
        if len(text) < 40:
            if platform in LOGIN_WALLED:
                raise ValueError(f"Serwis {platform} pokazuje treść tylko zalogowanym — wklej treść posta ręcznie")
            raise ValueError("Strona nie zawiera tekstu do analizy (treść ładowana przez JavaScript lub wymaga logowania)")
        return [Item(url=res.final_url, platform=platform, raw=res.text, raw_type="html", text=text,
                     author=_meta(soup, "author", "article:author") or ld_author, title=_meta(soup, "og:title") or "",
                     published_at=published)]
    return [Item(url=res.final_url, platform=platform, raw=res.text, raw_type="html", html=res.text, published_at=published)]


def collect_social(res: FetchResult) -> list[Item]:
    try:
        post = json.loads(res.text)
    except ValueError:
        # A link to the post page itself (not an API export): read it like any web page.
        return collect_html(res)
    posts = post if isinstance(post, list) else post.get("data", [post]) if isinstance(post, dict) and "data" in post else [post]
    items = []
    for p in posts:
        text = p.get("text") or p.get("caption") or p.get("message") or p.get("description") or ""
        items.append(Item(url=p.get("url") or p.get("permalink") or res.final_url, platform=p.get("platform", "social"),
                          raw=json.dumps(p, ensure_ascii=False), raw_type="json", text=text, author=p.get("author") or p.get("username"),
                          published_at=p.get("published_at") or p.get("created_time") or p.get("timestamp")))
    return items


def collect_meta_ads(res: FetchResult) -> list[Item]:
    try:
        payload = json.loads(res.text)
    except ValueError:
        raise ValueError("To nie jest odpowiedź Meta Ad Library API (JSON) — dodaj link jako „Strona WWW”") from None
    items = []
    for ad in payload.get("data", []):
        bodies = ad.get("ad_creative_bodies") or []
        titles = ad.get("ad_creative_link_titles") or []
        platforms = "/".join(ad.get("publisher_platforms") or ["meta"])
        items.append(Item(
            url=ad.get("ad_snapshot_url") or f"{res.final_url}#{ad.get('id')}", platform=f"{platforms} (reklama)",
            raw=json.dumps(ad, ensure_ascii=False), raw_type="json", text="\n".join(titles + bodies),
            author=ad.get("page_name"), published_at=ad.get("ad_delivery_start_time"),
        ))
    return items


REGISTER_CATEGORY = {
    "domy_maklerskie": "dom_maklerski",
    "banki_prowadzace": "bank",
    "oddzialy": "oddzial",
    "notyfikowane_firmy_inwestycyjne_oddzialy": "oddzial",
    "notyfikowane_zagraniczne": "transgraniczna",
}


def register_category(url: str) -> str:
    low = url.lower()
    for k, v in REGISTER_CATEGORY.items():
        if k in low:
            return v
    return "dom_maklerski"


def collect_knf_register(res: FetchResult) -> list[dict]:
    """Parses UKNF register tables. Each firm is a 2-column table with labelled rows."""
    soup = BeautifulSoup(res.text, "html.parser")
    entities: list[dict] = []
    for table in soup.find_all("table"):
        fields: dict[str, str] = {}
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(" ", strip=True).lower()
                value = cells[1].get_text("\n", strip=True)
                fields[label] = value
        name = next((v for k, v in fields.items() if k.startswith("nazwa") or "firma" in k), None)
        if not name:
            continue
        # One cell may list the current and former name on separate lines — keep each as an alias.
        names = [n.strip() for n in name.split("\n") if len(n.strip()) > 3]
        address = next((v for k, v in fields.items() if "adres" in k or "teleadres" in k), "")
        date = next((v for k, v in fields.items() if "data" in k), "")
        scope = next((v for k, v in fields.items() if "zakres" in k), "")
        country = next((v for k, v in fields.items() if "państwo" in k or "kraj" in k), "")
        for n in names:
            entities.append({"name": n, "address": (address + (f"\n{country}" if country else "")).replace("\n", ", "),
                             "license_date": date, "scope": re.sub(r"\s+", " ", scope)})
    if not entities:
        # Fallback for list layouts: rows of a single table with a header.
        for tr in soup.select("table tr")[1:]:
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if tds and len(tds[0]) > 3:
                entities.append({"name": tds[0], "address": ", ".join(tds[1:2]), "license_date": "", "scope": ""})
    return entities


def next_page_url(res: FetchResult, visited: set[str]) -> str | None:
    """Follows UKNF register pagination (`?page=N`)."""
    from urllib.parse import urljoin

    soup = BeautifulSoup(res.text, "html.parser")
    current = re.search(r"[?&]page=(\d+)", res.final_url)
    want = (int(current.group(1)) if current else 1) + 1
    for a in soup.find_all("a", href=True):
        m = re.search(r"[?&]page=(\d+)", a["href"])
        if m and int(m.group(1)) == want:
            url = urljoin(res.final_url, a["href"])
            return None if url in visited else url
    return None


COLLECTORS = {"html": collect_html, "social": collect_social, "meta_ads": collect_meta_ads}
