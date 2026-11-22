"""Module 2 — risk-information compliance (18 criteria from the UKNF resource).

Each rule returns PASS / FAIL / WARN / NA with evidence and its legal basis.
Rules evaluate the *presentation* of risk information (size, contrast,
placement, collapsing, language) as well as the wording.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from statistics import mean

from . import lexicon as L
from .preprocess import Block, Document, contrast_ratio, detect_language, normalize

PASS, FAIL, WARN, NA = "pass", "fail", "warn", "na"


@dataclass
class RuleResult:
    id: str
    name: str
    status: str
    detail: str
    legal_basis: str
    weight: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuleSpec:
    id: str
    name: str
    legal_basis: str
    weight: float  # contribution to the noisy-OR score when the rule fails (0..1)
    description: str


SPECS: dict[str, RuleSpec] = {s.id: s for s in [
    RuleSpec("1", "Identyfikacja firmy", "art. 44 ust. 2 lit. a rozporządzenia del. 2017/565", 0.18,
             "Materiał zawiera oficjalną nazwę firmy inwestycyjnej."),
    RuleSpec("2", "Oznaczenie reklamy", "art. 24 ust. 3 MiFID II", 0.15,
             "Materiał reklamowy jest jednoznacznie oznaczony jako reklama."),
    RuleSpec("3", "Informacja o ryzyku", "art. 44 ust. 2 lit. b rozporządzenia del. 2017/565", 0.45,
             "Twierdzeniom o zyskach bezpośrednio towarzyszy informacja o istotnym ryzyku."),
    RuleSpec("4", "Rozmiar czcionki ryzyka", "art. 44 ust. 2 lit. c rozporządzenia del. 2017/565", 0.3,
             "Czcionka informacji o ryzyku nie jest mniejsza od przeważającej czcionki materiału."),
    RuleSpec("5", "Ekspozycja i kontrast ryzyka", "art. 44 ust. 2 lit. c i e rozporządzenia del. 2017/565", 0.3,
             "Informacja o ryzyku ma wystarczający kontrast i nie jest przesłonięta."),
    RuleSpec("6", "Zakrywanie / ukrywanie ryzyka", "art. 44 ust. 2 lit. e rozporządzenia del. 2017/565", 0.3,
             "Ryzyko nie jest ukryte w przypisach, sekcji „Legal” ani w miejscach o niskiej widoczności."),
    RuleSpec("7", "Dostępność za 1 kliknięciem", "art. 44 ust. 2 lit. b i e rozporządzenia del. 2017/565", 0.28,
             "Informacja o ryzyku jest widoczna bez rozwijania, klikania ani przechodzenia na inną warstwę."),
    RuleSpec("8", "Responsywność (różne urządzenia)", "art. 44 ust. 2 lit. g rozporządzenia del. 2017/565", 0.2,
             "Tekst o ryzyku nie jest ucinany ani skalowany poniżej czytelności na telefonie, tablecie i desktopie."),
    RuleSpec("9", "Zrozumiałość dla grupy docelowej", "art. 44 ust. 2 lit. d rozporządzenia del. 2017/565", 0.12,
             "Ostrzeżenie o ryzyku jest napisane językiem zrozumiałym dla przeciętnego odbiorcy."),
    RuleSpec("10", "Spójność językowa", "art. 44 ust. 2 lit. f rozporządzenia del. 2017/565", 0.25,
             "Informacja o ryzyku jest w tym samym języku co główny przekaz."),
    RuleSpec("11", "Porównania produktów / usług", "art. 44 ust. 3 rozporządzenia del. 2017/565", 0.2,
             "Porównania wskazują źródło informacji i przyjęte założenia."),
    RuleSpec("12a", "Wyniki historyczne — okres i zakres", "art. 44 ust. 4 rozporządzenia del. 2017/565", 0.15,
             "Wyniki obejmują ostatnie 5 lat, pełne okresy 12-miesięczne, z okresem referencyjnym i źródłem."),
    RuleSpec("12b", "Wyniki historyczne — warunki i waluta", "art. 44 ust. 4 rozporządzenia del. 2017/565", 0.12,
             "Wskazano wpływ kursów walut oraz prowizji, opłat i obciążeń na wyniki."),
    RuleSpec("13", "Dominacja wyników historycznych", "art. 44 ust. 4 lit. a rozporządzenia del. 2017/565", 0.15,
             "Wyniki historyczne nie są najbardziej wyeksponowanym elementem materiału."),
    RuleSpec("14", "Ostrzeżenie przy wynikach historycznych", "art. 44 ust. 4 lit. d rozporządzenia del. 2017/565", 0.25,
             "Zastrzeżenie, że wyniki historyczne nie są wiarygodnym wskaźnikiem przyszłych wyników."),
    RuleSpec("15", "Prognozy przyszłych wyników", "art. 44 ust. 6 rozporządzenia del. 2017/565", 0.35,
             "Prognozom towarzyszy ostrzeżenie, że nie są wiarygodnym wskaźnikiem przyszłych wyników."),
    RuleSpec("16", "Informacja podatkowa", "art. 44 ust. 7 rozporządzenia del. 2017/565", 0.25,
             "Przy odwołaniu do podatków wskazano zależność od indywidualnej sytuacji i możliwość zmian."),
    RuleSpec("17", "Zakaz sugerowania aprobaty organu nadzoru", "art. 44 ust. 8 rozporządzenia del. 2017/565", 0.4,
             "Odwołania do KNF nie sugerują zatwierdzenia ani aprobaty produktu lub usługi."),
    RuleSpec("18", "Nadzór jako argument bezpieczeństwa", "art. 44 ust. 8 rozporządzenia del. 2017/565", 0.35,
             "Odwołania do nadzoru nie są używane jako argument za bezpieczeństwem inwestycji."),
]}


def _clip(text: str, n: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


class Context:
    """Pre-computed facts shared by the rules."""

    def __init__(self, doc: Document):
        self.doc = doc
        self.blocks = doc.blocks
        self.norm = [normalize(b.text) for b in doc.blocks]
        self.full = " ".join(self.norm)
        self.profit_idx = [i for i, t in enumerate(self.norm) if L.PROFIT.search(t)]
        # A risk *statement* — not a heading, a <summary> toggle or a link label.
        self.risk_idx = [
            i for i, t in enumerate(self.norm)
            if L.RISK.search(t) and len(t) > 40 and self.blocks[i].heading_level is None
            and self.blocks[i].tag not in ("summary", "a", "button")
        ]
        self.risk_visible_idx = [i for i in self.risk_idx if self.blocks[i].visible and not self.blocks[i].in_footnote]
        # Prevailing font size: length-weighted mode over visible body text,
        # excluding the risk statements themselves (they are what we compare).
        weights: dict[float, int] = {}
        risk_set = set(self.risk_idx)
        for i, b in enumerate(doc.blocks):
            if b.visible and b.heading_level is None and i not in risk_set:
                weights[round(b.style.font_px)] = weights.get(round(b.style.font_px), 0) + len(b.text)
        self.main_font = max(weights, key=weights.get) if weights else 16.0
        main_texts = [b.text for b in doc.blocks if b.visible and not b.in_footnote and b.heading_level is None]
        self.main_lang = detect_language(" ".join(main_texts)) if main_texts else "unknown"
        self.risk_main_lang_idx = [
            i for i in self.risk_visible_idx
            if self.main_lang == "unknown" or detect_language(self.blocks[i].text) in (self.main_lang, "unknown")
        ]
        self.promotional = bool(L.PROMO.search(self.full) or self.profit_idx or L.AD_LABEL.search(self.full))

    def risk_blocks(self) -> list[Block]:
        return [self.blocks[i] for i in self.risk_idx]

    def find(self, pattern: re.Pattern[str]) -> list[int]:
        return [i for i, t in enumerate(self.norm) if pattern.search(t)]


def evaluate(doc: Document, firm_names: list[str]) -> list[RuleResult]:
    ctx = Context(doc)
    results: list[RuleResult] = []

    def add(rule_id: str, status: str, detail: str, evidence: list[str] | None = None) -> None:
        s = SPECS[rule_id]
        results.append(RuleResult(s.id, s.name, status, detail, s.legal_basis, s.weight, [_clip(e) for e in (evidence or [])][:3]))

    # 1 — firm identification
    if firm_names:
        add("1", PASS, f"Wskazano firmę: {firm_names[0].rstrip('.')}.", [firm_names[0]])
    elif (i := ctx.find(L.COMPANY_FORM)):
        add("1", PASS, "Wskazano podmiot z formą prawną.", [ctx.blocks[i[0]].text])
    else:
        add("1", FAIL, "Nie znaleziono oficjalnej nazwy firmy inwestycyjnej.")

    # 2 — advertisement label
    if not ctx.promotional:
        add("2", NA, "Materiał nie ma cech reklamy.")
    elif (i := ctx.find(L.AD_LABEL)):
        add("2", PASS, "Materiał oznaczono jako reklamę.", [ctx.blocks[i[0]].text])
    else:
        add("2", FAIL, "Materiał promocyjny nie jest oznaczony jako reklama.")

    # 3 — risk accompanies profit claims
    if not ctx.profit_idx:
        add("3", NA, "Brak twierdzeń o zyskach.")
    elif not ctx.risk_idx:
        add("3", FAIL, "Twierdzeniom o zyskach nie towarzyszy żadna informacja o ryzyku.",
            [ctx.blocks[ctx.profit_idx[0]].text])
    else:
        near = [p for p in ctx.profit_idx if any(abs(p - r) <= 2 for r in ctx.risk_main_lang_idx)]
        if ctx.risk_visible_idx and not ctx.risk_main_lang_idx:
            add("3", FAIL, "Informacja o ryzyku jest podana wyłącznie w innym języku niż przekaz o zyskach.",
                [ctx.blocks[ctx.risk_visible_idx[0]].text])
        elif len(near) == len(ctx.profit_idx):
            add("3", PASS, "Informacja o ryzyku występuje bezpośrednio przy twierdzeniach o zyskach.",
                [ctx.blocks[ctx.risk_visible_idx[0]].text])
        elif ctx.risk_visible_idx:
            add("3", WARN, "Informacja o ryzyku jest w materiale, ale nie bezpośrednio przy wszystkich twierdzeniach o zyskach.",
                [ctx.blocks[p].text for p in ctx.profit_idx if p not in near])
        else:
            add("3", FAIL, "Informacja o ryzyku istnieje tylko w miejscach o ograniczonej widoczności.",
                [ctx.blocks[ctx.risk_idx[0]].text])

    risk_blocks = ctx.risk_blocks()

    # 4 — risk font size
    if not risk_blocks:
        add("4", NA, "Brak informacji o ryzyku do oceny.")
    else:
        best = max(b.style.font_px for b in risk_blocks)
        ratio = best / ctx.main_font
        detail = f"Ryzyko: {best:.0f}px, przeważająca czcionka: {ctx.main_font:.0f}px ({ratio:.0%})."
        if ratio < 0.8:
            add("4", FAIL, "Czcionka ryzyka jest wyraźnie mniejsza. " + detail, [risk_blocks[0].text])
        elif ratio < 0.95:
            add("4", WARN, "Czcionka ryzyka jest nieco mniejsza. " + detail, [risk_blocks[0].text])
        else:
            add("4", PASS, detail)

    # 5 — contrast and exposure
    if not risk_blocks:
        add("5", NA, "Brak informacji o ryzyku do oceny.")
    else:
        ratios = []
        for b in risk_blocks:
            if b.style.color and b.style.background:
                r = contrast_ratio(b.style.color, b.style.background)
                if b.style.opacity < 1:
                    r = 1 + (r - 1) * b.style.opacity
                ratios.append((r, b))
        if not ratios:
            add("5", WARN, "Nie udało się ustalić kolorów tekstu o ryzyku.")
        else:
            r, b = max(ratios, key=lambda x: x[0])
            if r < 3:
                add("5", FAIL, f"Kontrast tekstu o ryzyku {r:.1f}:1 (wymagane min. 4,5:1).", [b.text])
            elif r < 4.5:
                add("5", WARN, f"Kontrast tekstu o ryzyku {r:.1f}:1 — poniżej zalecanych 4,5:1.", [b.text])
            else:
                add("5", PASS, f"Kontrast tekstu o ryzyku {r:.1f}:1.")

    # 6 — hiding in footnotes / legal sections
    if not risk_blocks:
        add("6", NA, "Brak informacji o ryzyku do oceny.")
    elif ctx.risk_visible_idx:
        add("6", PASS, "Informacja o ryzyku jest w głównej treści materiału.")
    else:
        where = "przypisie / sekcji prawnej" if any(b.in_footnote for b in risk_blocks) else "elemencie ukrytym"
        add("6", FAIL, f"Informacja o ryzyku występuje wyłącznie w {where}.", [risk_blocks[0].text])

    # 7 — available without an extra click
    risk_links = [b for b in ctx.blocks if b.link_href and re.search(r"ryzyk|risk", normalize(b.text + " " + b.link_href))]
    collapsed_only = risk_blocks and all(b.collapsed or b.hidden for b in risk_blocks)
    if collapsed_only:
        add("7", FAIL, "Informacja o ryzyku wymaga rozwinięcia sekcji.", [risk_blocks[0].text])
    elif not risk_blocks and risk_links:
        add("7", FAIL, "Informacja o ryzyku jest dostępna dopiero po kliknięciu linku.", [risk_links[0].text])
    elif not risk_blocks:
        add("7", NA, "Brak informacji o ryzyku do oceny.")
    else:
        add("7", PASS, "Informacja o ryzyku jest widoczna bez dodatkowych kliknięć.")

    # 8 — responsiveness (static simulation for 360 / 768 / 1280 px viewports)
    if not risk_blocks:
        add("8", NA, "Brak informacji o ryzyku do oceny.")
    else:
        issues = []
        for b in risk_blocks:
            if b.style.fixed_width_px and b.style.fixed_width_px > 360:
                issues.append(f"stała szerokość {b.style.fixed_width_px:.0f}px — ucinanie na telefonie (360px)")
            if b.style.nowrap and len(b.text) > 45:
                issues.append("tekst bez zawijania (white-space: nowrap) — ucinanie na wąskich ekranach")
            if b.style.viewport_font and b.style.font_px < 12:
                issues.append("czcionka w jednostkach vw skaluje się poniżej czytelności na telefonie")
        if not doc.has_viewport_meta and doc.url.startswith("http") and not doc.url.endswith(".json"):
            issues.append("brak meta viewport — strona skalowana na urządzeniach mobilnych")
        if any("ucinanie" in i or "vw" in i for i in issues):
            add("8", FAIL, "; ".join(sorted(set(issues))).capitalize() + ".", [risk_blocks[0].text])
        elif issues:
            add("8", WARN, "; ".join(sorted(set(issues))).capitalize() + ".")
        else:
            add("8", PASS, "Tekst o ryzyku pozostaje czytelny na telefonie, tablecie i desktopie (symulacja statyczna).")

    # 9 — comprehensibility (sentence length, long words, jargon)
    if not risk_blocks:
        add("9", NA, "Brak informacji o ryzyku do oceny.")
    else:
        text = " ".join(b.text for b in risk_blocks)
        sentences = [s for s in re.split(r"[.!?;]+", text) if s.strip()]
        words = re.findall(r"\w+", text)
        avg_len = mean(len(re.findall(r"\w+", s)) for s in sentences) if sentences else 0
        long_ratio = sum(1 for w in words if len(re.findall(r"[aeiouyąęó]", w.lower())) >= 4) / max(1, len(words))
        jargon = L.JARGON.findall(normalize(text))
        fog = 0.4 * (avg_len + 100 * long_ratio)
        detail = f"Średnio {avg_len:.0f} słów w zdaniu, {long_ratio:.0%} długich słów, indeks FOG ≈ {fog:.0f}."
        # Thresholds tuned for Polish, whose words are longer than English ones.
        if fog > 22 or len(jargon) >= 3:
            add("9", FAIL, "Ostrzeżenie trudne w odbiorze. " + detail + (f" Żargon: {', '.join(sorted(set(jargon)))}." if jargon else ""), [text])
        elif fog > 18 or jargon:
            add("9", WARN, "Ostrzeżenie może być trudne dla części odbiorców. " + detail)
        else:
            add("9", PASS, detail)

    # 10 — language consistency
    if not risk_blocks:
        add("10", NA, "Brak informacji o ryzyku do oceny.")
    else:
        langs = {detect_language(b.text) for b in risk_blocks} - {"unknown"}
        if ctx.main_lang != "unknown" and langs and ctx.main_lang not in langs:
            add("10", FAIL, f"Główny przekaz: {ctx.main_lang.upper()}, informacja o ryzyku: {', '.join(l.upper() for l in langs)}.",
                [risk_blocks[0].text])
        else:
            add("10", PASS, "Informacja o ryzyku jest w języku głównego przekazu.")

    # 11 — comparisons
    comp = ctx.find(L.COMPARISON)
    if not comp:
        add("11", NA, "Nie wykryto porównań produktów lub usług.")
    elif L.SOURCE.search(ctx.full):
        add("11", PASS, "Porównanie zawiera wskazanie źródła.", [ctx.blocks[comp[0]].text])
    else:
        add("11", FAIL, "Porównanie bez wskazania źródła informacji i założeń.", [ctx.blocks[comp[0]].text])

    # 12a / 12b / 13 / 14 — historical performance
    hist = ctx.find(L.HISTORICAL)
    hist = [i for i in hist if L.PROFIT.search(ctx.norm[i]) or re.search(r"\d+[.,]?\d*\s?%", ctx.norm[i])]
    if not hist:
        for rid in ("12a", "12b", "13", "14"):
            add(rid, NA, "Nie wykryto wyników historycznych.")
    else:
        ev = [ctx.blocks[hist[0]].text]
        missing = []
        if not L.FIVE_YEARS.search(ctx.full):
            missing.append("okresu 5 lat")
        if not L.FULL_PERIODS.search(ctx.full):
            missing.append("pełnych okresów 12-miesięcznych / okresu referencyjnego")
        if not L.SOURCE.search(ctx.full):
            missing.append("źródła danych")
        add("12a", FAIL if missing else PASS, ("Brak: " + ", ".join(missing) + ".") if missing else "Okres, zakres i źródło wskazane.", ev)

        missing_b = []
        if L.FX.search(ctx.full) and not L.FX_WARNING.search(ctx.full):
            missing_b.append("ostrzeżenia o wpływie kursów walut")
        if not L.FEES.search(ctx.full):
            missing_b.append("informacji o wpływie prowizji i opłat")
        add("12b", FAIL if missing_b else PASS, ("Brak " + " oraz ".join(missing_b) + ".") if missing_b else "Wskazano wpływ opłat i walut.", ev)

        dominant = [i for i in hist if ctx.blocks[i].heading_level in (1, 2) or ctx.blocks[i].style.font_px >= ctx.main_font * 1.6]
        add("13", FAIL if dominant else PASS,
            "Wyniki historyczne są najbardziej wyeksponowanym elementem (nagłówek / największa czcionka)." if dominant
            else "Wyniki historyczne nie dominują przekazu.", [ctx.blocks[dominant[0]].text] if dominant else [])

        add("14", PASS if L.PAST_NOT_INDICATOR.search(ctx.full) else FAIL,
            "Zawarto zastrzeżenie o wynikach historycznych." if L.PAST_NOT_INDICATOR.search(ctx.full)
            else "Brak zastrzeżenia, że wyniki historyczne nie są wiarygodnym wskaźnikiem przyszłych wyników.", ev)

    # 15 — forecasts
    fc = ctx.find(L.FORECAST)
    if not fc:
        add("15", NA, "Nie wykryto prognoz przyszłych wyników.")
    elif L.FORECAST_WARNING.search(ctx.full):
        add("15", WARN, "Wykryto prognozę (zgłoszona w raporcie); zawiera wymagane ostrzeżenie.", [ctx.blocks[fc[0]].text])
    else:
        add("15", FAIL, "Wykryto prognozę bez ostrzeżenia, że nie jest wiarygodnym wskaźnikiem przyszłych wyników.",
            [ctx.blocks[fc[0]].text])

    # 16 — tax treatment
    tx = ctx.find(L.TAX)
    if not tx:
        add("16", NA, "Brak odwołań do kwestii podatkowych.")
    else:
        lacks = []
        if not L.TAX_CAVEAT_INDIVIDUAL.search(ctx.full):
            lacks.append("zależności od indywidualnej sytuacji klienta")
        if not L.TAX_CAVEAT_CHANGE.search(ctx.full):
            lacks.append("możliwości zmian przepisów")
        add("16", FAIL if lacks else PASS, ("Brak informacji o " + " i ".join(lacks) + ".") if lacks
            else "Zawarto wymagane zastrzeżenia podatkowe.", [ctx.blocks[tx[0]].text])

    # 17 / 18 — supervisory authority
    knf = ctx.find(L.KNF)
    if not knf:
        add("17", NA, "Brak odwołań do organu nadzoru.")
        add("18", NA, "Brak odwołań do organu nadzoru.")
    else:
        approval = [i for i in knf if L.APPROVAL.search(ctx.norm[i])]
        safety = [i for i in knf if L.SAFETY.search(ctx.norm[i])]
        add("17", FAIL if approval else PASS,
            "Odwołanie do KNF sugeruje zatwierdzenie lub aprobatę produktu." if approval
            else "Odwołanie do KNF ma charakter informacyjny.", [ctx.blocks[i].text for i in (approval or knf[:1])])
        add("18", FAIL if safety else PASS,
            "Nadzór KNF użyty jako argument za bezpieczeństwem inwestycji." if safety
            else "Nadzór nie jest przedstawiany jako gwarancja bezpieczeństwa.", [ctx.blocks[i].text for i in (safety or knf[:1])])

    order = list(SPECS)
    results.sort(key=lambda r: order.index(r.id))
    return results


def score(results: list[RuleResult]) -> float:
    """Noisy-OR over failed (full weight) and warned (40% weight) rules -> 0..100."""
    p_ok = 1.0
    for r in results:
        if r.status == FAIL:
            p_ok *= 1 - r.weight
        elif r.status == WARN:
            p_ok *= 1 - r.weight * 0.4
    return round(100 * (1 - p_ok), 1)
