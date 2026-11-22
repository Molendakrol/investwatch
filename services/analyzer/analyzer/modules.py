"""Module 1 (third-party promotion) and Module 3 (shadow advisory)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import lexicon as L
from .preprocess import Document, normalize
from .register import Register, RegisterEntry, key
from .vectors import ADVISORY


@dataclass
class Signal:
    code: str
    label: str
    weight: float
    evidence: str = ""


@dataclass
class ModuleResult:
    module: str
    applicable: bool
    score: float
    summary: str
    entity: str | None = None
    firm: str | None = None
    firm_category: str | None = None
    advertiser: str | None = None
    signals: list[Signal] = field(default_factory=list)


def _noisy_or(signals: list[Signal]) -> float:
    p = 1.0
    for s in signals:
        p *= 1 - max(0.0, min(0.99, s.weight))
    return round(100 * (1 - p), 1)


def _first(pattern: re.Pattern[str], doc: Document) -> str:
    for b in doc.blocks:
        if pattern.search(normalize(b.text)):
            return b.text[:220]
    return ""


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def _publisher(doc: Document) -> str:
    return doc.author or doc.site_name or _host(doc.url) or "nieznany"


def _is_own_channel(doc: Document, firm: RegisterEntry) -> bool:
    """True when the material is published by the firm itself (own site / profile)."""
    k = key(firm.name)
    pub = key(_publisher(doc))
    host = re.sub(r"[^a-z0-9]", " ", _host(doc.url))
    tokens = [t for t in k.split() if len(t) > 3 and t not in ("dom", "maklerski", "invest", "capital", "markets")]
    if pub and (pub == k or (len(pub) > 5 and (pub in k or k in pub))):
        return True
    return any(t in host.split() or t in pub.split() for t in tokens)


# ------------------------------------------------------------------ module 1

def module1(doc: Document, register: Register) -> ModuleResult:
    firms = register.find_mentions(doc.text)
    if not firms:
        return ModuleResult("m1", False, 0.0, "Brak wzmianek o firmach z rejestru.")
    firm = firms[0]
    publisher = _publisher(doc)
    if publisher == "nieznany" or doc.url.startswith("about:"):
        # Pasted material without publisher metadata: an advertiser cannot be attributed,
        # so it is assessed as the firm's own marketing (module 2).
        return ModuleResult("m1", False, 0.0, "Brak danych o publikującym — ocena w module 2.",
                            firm=firm.name, firm_category=firm.category)
    own = _is_own_channel(doc, firm)
    if own:
        return ModuleResult("m1", False, 0.0, f"Materiał własny firmy {firm.name} — oceniany w module 2.",
                            firm=firm.name, firm_category=firm.category, advertiser=publisher)
    full = normalize(doc.text)
    signals = [Signal("firm", f"Wzmianka o firmie z rejestru: {firm.name}", 0.35, firm.name)]
    if L.AFFILIATE.search(full):
        signals.append(Signal("affiliate", "Link / kod polecający lub oznaczenie współpracy", 0.55, _first(L.AFFILIATE, doc)))
    if L.PROMO.search(full):
        signals.append(Signal("cta", "Wezwanie do założenia konta lub skorzystania z oferty", 0.35, _first(L.PROMO, doc)))
    if L.PROFIT.search(full):
        signals.append(Signal("profit", "Eksponowanie zysków", 0.2, _first(L.PROFIT, doc)))
    if L.AD_LABEL.search(full):
        signals.append(Signal("labelled", "Treść oznaczona jako reklama / współpraca", 0.25, _first(L.AD_LABEL, doc)))
    elif L.AFFILIATE.search(full) or L.PROMO.search(full):
        signals.append(Signal("unlabelled", "Treść promocyjna bez oznaczenia reklamy", 0.2))
    if not L.RISK.search(full) and L.PROFIT.search(full):
        signals.append(Signal("no_risk", "Brak informacji o ryzyku przy promocji", 0.15))
    if firm.category in ("transgraniczna", "oddzial") or "ltd" in normalize(firm.name):
        signals.append(Signal("crossborder", "Firma zagraniczna działająca w Polsce transgranicznie", 0.05))
    sc = _noisy_or(signals)
    if not any(s.code in ("affiliate", "cta", "labelled") for s in signals):
        sc = min(sc, 40.0)  # a bare mention (news, review) is not an advertisement
    return ModuleResult(
        "m1", True, sc,
        f"{publisher} promuje {firm.name}" if sc >= 50 else f"{publisher} wspomina {firm.name}",
        entity=publisher, firm=firm.name, firm_category=firm.category, advertiser=publisher, signals=signals,
    )


# ------------------------------------------------------------------ module 3

ENTITY_RX = re.compile(
    r"([A-ZŁŚŻŹĆ][\w&.\-]*(?:\s+(?:&\s+)?[A-ZŁŚŻŹĆ][\w&.\-]*){0,4}\s+(?:Family Office|Wealth Management|Capital|Partners|Advisory|Consulting|Invest(?:ment)?s?)"
    r"(?:\s+(?:Sp\. z o\.o\.|S\.A\.|Ltd))?)"
)


def _entity_name(doc: Document) -> str:
    for b in doc.blocks[:40]:
        m = ENTITY_RX.search(b.text)
        if m:
            return m.group(1).strip()
    return doc.site_name or doc.author or (doc.title.split("|")[0].split("—")[0].strip() if doc.title else _host(doc.url))


def module3(doc: Document, register: Register, llm_hint: float | None = None) -> ModuleResult:
    full = normalize(doc.text)
    strong = L.ADVICE_STRONG.findall(full)
    context = L.ADVICE_CONTEXT.findall(full)
    if not strong and not context:
        return ModuleResult("m3", False, 0.0, "Brak sformułowań wskazujących na doradztwo inwestycyjne.")
    entity = _entity_name(doc)
    reg = register.lookup(entity) or next(iter(register.find_mentions(entity)), None)
    signals: list[Signal] = []
    if strong:
        signals.append(Signal("advice", f"Sformułowania o doradztwie ({len(set(strong))})", min(0.6, 0.3 + 0.1 * len(set(strong))),
                              _first(L.ADVICE_STRONG, doc)))
    if context:
        signals.append(Signal("personal", "Rekomendacje dopasowane do sytuacji klienta", 0.35, _first(L.ADVICE_CONTEXT, doc)))
    if L.INSTRUMENT.search(full):
        signals.append(Signal("instrument", "Dotyczy instrumentów finansowych", 0.25, _first(L.INSTRUMENT, doc)))
    if L.FEE_FOR_ADVICE.search(full):
        signals.append(Signal("paid", "Odpłatna usługa (abonament, konsultacja, success fee)", 0.3, _first(L.FEE_FOR_ADVICE, doc)))
    if L.GUARANTEE.search(full):
        signals.append(Signal("guarantee", "Obietnica gwarantowanego zysku", 0.25, _first(L.GUARANTEE, doc)))
    proto = ADVISORY.predict(doc.visible_text or doc.text)
    if proto > 0.55:
        signals.append(Signal("semantic", f"Podobieństwo semantyczne do ofert doradczych ({proto:.0%})", (proto - 0.5) * 0.8))
    if llm_hint is not None and llm_hint > 0.5:
        signals.append(Signal("llm", f"Model językowy: prawdopodobne doradztwo ({llm_hint:.0%})", (llm_hint - 0.5) * 0.8))

    sc = _noisy_or(signals)
    if L.EDUCATION_ONLY.search(full) and not context:
        sc *= 0.45
        signals.append(Signal("education", "Zastrzeżenie o charakterze edukacyjnym", 0.0, _first(L.EDUCATION_ONLY, doc)))
    if reg is not None:
        if reg.authorised_for_advice:
            sc *= 0.15
            summary = f"{entity}: podmiot w rejestrze firm inwestycyjnych (zezwolenie obejmuje doradztwo)"
            signals.append(Signal("register_ok", f"W rejestrze: {reg.name}", 0.0))
        else:
            sc *= 0.4
            summary = f"{entity}: podmiot w rejestrze — zweryfikuj, czy zakres zezwolenia obejmuje doradztwo"
            signals.append(Signal("register_scope", f"W rejestrze bez doradztwa: {reg.name}", 0.0))
    else:
        signals.append(Signal("register_missing", "Podmiotu nie ma w rejestrze firm inwestycyjnych", 0.0))
        summary = f"{entity}: oferta doradcza, podmiotu brak w rejestrze firm inwestycyjnych"
    return ModuleResult("m3", True, round(sc, 1), summary, entity=entity, firm=reg.name if reg else None,
                        firm_category=reg.category if reg else None, signals=signals)
