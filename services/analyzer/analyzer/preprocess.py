"""HTML -> structured document.

Turns raw HTML into text *blocks* that keep the presentation facts the
compliance rules need: effective font size, colours, whether the text is
hidden, collapsed, placed in a footnote/legal area, or inside a heading.
Only a small, predictable subset of CSS is resolved (inline styles plus
simple tag / .class / #id selectors from <style> elements) — enough for
marketing pages, and documented as a known limitation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

BLOCK_TAGS = {
    "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "blockquote",
    "figcaption", "dd", "dt", "summary", "caption", "label", "button", "a",
    "div", "section", "article", "aside", "footer", "header", "main", "span", "small",
}
HEADING_SIZES = {"h1": 32.0, "h2": 24.0, "h3": 20.0, "h4": 18.0, "h5": 16.0, "h6": 14.0}
TAG_SCALE = {"small": 0.8, "sub": 0.75, "sup": 0.75}
LOW_VISIBILITY_HINTS = re.compile(
    r"foot|legal|disclaimer|przypis|nota|fine-?print|terms|regulamin|copyright|small-?print|stopka", re.I
)
COLLAPSE_HINTS = re.compile(r"collaps|accordion|toggle|expand|rozwi|more-info|hidden-content", re.I)
DROP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "head"}


@dataclass
class Style:
    font_px: float = 16.0
    color: tuple[int, int, int] | None = (0, 0, 0)
    background: tuple[int, int, int] | None = (255, 255, 255)
    hidden: bool = False
    opacity: float = 1.0
    fixed_width_px: float | None = None
    nowrap: bool = False
    viewport_font: bool = False


@dataclass
class Block:
    index: int
    text: str
    tag: str
    style: Style
    heading_level: int | None = None
    in_footnote: bool = False
    collapsed: bool = False
    hidden: bool = False
    link_href: str | None = None

    @property
    def visible(self) -> bool:
        return not self.hidden and not self.collapsed and self.style.opacity > 0.2


@dataclass
class Document:
    url: str
    title: str
    author: str | None
    site_name: str | None
    lang_attr: str | None
    has_viewport_meta: bool
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks)

    @property
    def visible_text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.visible)


# ---------------------------------------------------------------- text utils

def normalize(text: str) -> str:
    """Lower-case, fold Polish diacritics and collapse whitespace (for matching)."""
    text = text.replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def simhash(text: str, bits: int = 64) -> int:
    """64-bit SimHash over word 3-shingles — near-duplicate detection."""
    words = normalize(text).split()
    shingles = [" ".join(words[i : i + 3]) for i in range(max(1, len(words) - 2))]
    acc = [0] * bits
    for sh in shingles:
        h = int.from_bytes(hashlib.blake2b(sh.encode(), digest_size=8).digest(), "big")
        for i in range(bits):
            acc[i] += 1 if h >> i & 1 else -1
    return sum(1 << i for i, v in enumerate(acc) if v > 0)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


_PL_WORDS = set("i w z na nie się jest to że do o od po dla jak lub oraz przez może mogą który która które jeśli są być".split())
_EN_WORDS = set("the and of to in is are be may can your you for with or not this that past future capital".split())


def detect_language(text: str) -> str:
    """Tiny stop-word language guesser (pl / en / unknown) — enough for rule 10."""
    words = re.findall(r"[a-ząćęłńóśźż]+", text.lower())
    if not words:
        return "unknown"
    pl = sum(w in _PL_WORDS for w in words) + sum(any(c in w for c in "ąćęłńóśźż") for w in words)
    en = sum(w in _EN_WORDS for w in words)
    if pl == en == 0:
        return "unknown"
    return "pl" if pl >= en else "en"


# ---------------------------------------------------------------- css utils

_NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "silver": (192, 192, 192), "lightgray": (211, 211, 211), "lightgrey": (211, 211, 211),
    "darkgray": (169, 169, 169), "red": (255, 0, 0), "navy": (0, 0, 128), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "gold": (255, 215, 0), "orange": (255, 165, 0), "green": (0, 128, 0),
    "whitesmoke": (245, 245, 245), "gainsboro": (220, 220, 220),
}


def parse_color(value: str) -> tuple[int, int, int] | None:
    v = value.strip().lower()
    if v in ("transparent", "inherit", "initial", "none", ""):
        return None
    if v in _NAMED:
        return _NAMED[v]
    m = re.match(r"#([0-9a-f]{3}|[0-9a-f]{6})\b", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = re.match(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+))?", v)
    if m:
        if m.group(4) is not None and float(m.group(4)) == 0:
            return None
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG 2.x contrast ratio."""

    def lum(c: tuple[int, int, int]) -> float:
        def ch(x: int) -> float:
            s = x / 255
            return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

        r, g, b = (ch(x) for x in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1, l2 = sorted((lum(fg), lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def parse_declarations(css: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in css.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip().replace("!important", "").strip()
    return out


def parse_stylesheet(css: str) -> list[tuple[str, dict[str, str]]]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^}]*\})*[^}]*\}", "", css)
    rules = []
    for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        decl = parse_declarations(body)
        for s in sel.split(","):
            s = s.strip()
            if s:
                rules.append((s, decl))
    return rules


def _selector_matches(selector: str, el: Tag) -> bool:
    # Support only the last simple selector (tag, .class, #id, tag.class).
    last = selector.split()[-1]
    m = re.fullmatch(r"([a-z0-9]*)((?:\.[\w-]+)*)(#[\w-]+)?((?:\.[\w-]+)*)", last, re.I)
    if not m:
        return False
    tag, cls1, id_, cls2 = m.groups()
    if tag and el.name != tag.lower():
        return False
    classes = [c for c in (cls1 + cls2).split(".") if c]
    el_classes = el.get("class") or []
    if any(c not in el_classes for c in classes):
        return False
    if id_ and el.get("id") != id_[1:]:
        return False
    return bool(tag or classes or id_)


def _font_px(value: str, parent_px: float) -> tuple[float, bool]:
    v = value.strip().lower()
    m = re.match(r"([\d.]+)\s*(px|pt|rem|em|%|vw)?", v)
    named = {"xx-small": 9, "x-small": 10, "small": 13, "medium": 16, "large": 18, "x-large": 24, "xx-large": 32, "smaller": parent_px * 0.83, "larger": parent_px * 1.2}
    if v in named:
        return float(named[v]), False
    if not m:
        return parent_px, False
    n, unit = float(m.group(1)), (m.group(2) or "px")
    return {
        "px": n, "pt": n * 1.333, "rem": n * 16, "em": n * parent_px, "%": parent_px * n / 100, "vw": n * 3.75,
    }[unit], unit == "vw"


# ---------------------------------------------------------------- main entry

def parse_html(html: str, url: str = "") -> Document:
    soup = BeautifulSoup(html, "html.parser")
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    sheet: list[tuple[str, dict[str, str]]] = []
    for st in soup.find_all("style"):
        sheet.extend(parse_stylesheet(st.get_text()))

    def meta(*names: str) -> str | None:
        for n in names:
            el = soup.find("meta", attrs={"name": n}) or soup.find("meta", attrs={"property": n})
            if el and el.get("content"):
                return el["content"].strip()
        return None

    html_el = soup.find("html")
    doc = Document(
        url=url,
        title=(soup.title.get_text(strip=True) if soup.title else "") or (meta("og:title") or ""),
        author=meta("author", "article:author", "twitter:creator"),
        site_name=meta("og:site_name", "application-name"),
        lang_attr=(html_el.get("lang") if html_el else None),
        has_viewport_meta=bool(soup.find("meta", attrs={"name": "viewport"})),
    )

    for t in soup.find_all(list(DROP_TAGS)):
        t.decompose()

    body = soup.body or soup
    style_cache: dict[int, Style] = {}

    def computed(el: Tag) -> Style:
        key = id(el)
        if key in style_cache:
            return style_cache[key]
        parent = el.parent if isinstance(el.parent, Tag) else None
        base = computed(parent) if parent is not None and parent is not soup else Style()
        st = Style(
            font_px=base.font_px, color=base.color, background=base.background, hidden=base.hidden,
            opacity=base.opacity, fixed_width_px=base.fixed_width_px, nowrap=base.nowrap,
            viewport_font=base.viewport_font,
        )
        if el.name in HEADING_SIZES:
            st.font_px = HEADING_SIZES[el.name]
        if el.name in TAG_SCALE:
            st.font_px = base.font_px * TAG_SCALE[el.name]
        decl: dict[str, str] = {}
        for sel, d in sheet:
            if _selector_matches(sel, el):
                decl.update(d)
        decl.update(parse_declarations(el.get("style", "")))
        if "font-size" in decl:
            st.font_px, vw = _font_px(decl["font-size"], base.font_px)
            st.viewport_font = st.viewport_font or vw
        if "color" in decl and (c := parse_color(decl["color"])):
            st.color = c
        for k in ("background-color", "background"):
            if k in decl and (c := parse_color(decl[k])):
                st.background = c
        if decl.get("display") == "none" or decl.get("visibility") == "hidden" or el.has_attr("hidden"):
            st.hidden = True
        if el.get("aria-hidden") == "true":
            st.hidden = True
        if "opacity" in decl:
            try:
                st.opacity = base.opacity * float(decl["opacity"])
            except ValueError:
                pass
        if "width" in decl and (m := re.match(r"([\d.]+)px", decl["width"])):
            st.fixed_width_px = float(m.group(1))
        if decl.get("white-space") == "nowrap":
            st.nowrap = True
        style_cache[key] = st
        return st

    def flags(el: Tag) -> tuple[bool, bool, int | None, str | None]:
        footnote = collapsed = False
        heading: int | None = None
        href: str | None = None
        node: Tag | None = el
        while isinstance(node, Tag) and node is not soup:
            name = node.name or ""
            ident = " ".join(node.get("class") or []) + " " + (node.get("id") or "")
            if name in ("footer", "small", "sup", "sub") or LOW_VISIBILITY_HINTS.search(ident):
                footnote = True
            if name == "details" and not node.has_attr("open"):
                # <summary> stays visible; everything else in a closed <details> is collapsed.
                if not (el.name == "summary" or el.find_parent("summary")):
                    collapsed = True
            if COLLAPSE_HINTS.search(ident) or node.get("aria-expanded") == "false":
                collapsed = True
            if name in HEADING_SIZES and heading is None:
                heading = int(name[1])
            if name == "a" and href is None:
                href = node.get("href")
            node = node.parent if isinstance(node.parent, Tag) else None
        return footnote, collapsed, heading, href

    # Group text nodes by their nearest block-level ancestor.
    groups: dict[int, tuple[Tag, list[str]]] = {}
    order: list[int] = []
    for s in body.find_all(string=True):
        if not isinstance(s, NavigableString):
            continue
        text = s.strip()
        if not text:
            continue
        parent = s.parent
        block = parent
        while isinstance(block, Tag) and block.name not in BLOCK_TAGS and block.parent is not None:
            block = block.parent
        anchor = parent if isinstance(parent, Tag) else block
        key = id(block)
        if key not in groups:
            groups[key] = (anchor, [])
            order.append(key)
        groups[key][1].append(text)

    for i, key in enumerate(order):
        anchor, parts = groups[key]
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if not text:
            continue
        st = computed(anchor)
        footnote, collapsed, heading, href = flags(anchor)
        doc.blocks.append(
            Block(
                index=len(doc.blocks), text=text, tag=anchor.name or "", style=st,
                heading_level=heading, in_footnote=footnote, collapsed=collapsed,
                hidden=st.hidden, link_href=href,
            )
        )
    return doc


def parse_text(text: str, url: str = "", author: str | None = None, title: str = "") -> Document:
    """Plain text (e.g. a social-media post) -> document with one block per paragraph."""
    doc = Document(url=url, title=title, author=author, site_name=None, lang_attr=None, has_viewport_meta=True)
    for i, para in enumerate(p.strip() for p in re.split(r"\n\s*\n|\n", text)):
        if para:
            doc.blocks.append(Block(index=i, text=para, tag="p", style=Style()))
    return doc
