"""Analysis pipeline: preprocess -> modules 1/2/3 -> unified assessments."""

from __future__ import annotations

from dataclasses import asdict

from . import lexicon as L
from . import llm
from .modules import module1, module3
from .preprocess import Document, content_hash, normalize, parse_html, parse_text, simhash
from .register import Register
from .rules_m2 import FAIL, WARN, evaluate, score

VERSION = "1.0.0"


def level(score_value: float) -> str:
    if score_value >= 85:
        return "critical"
    if score_value >= 70:
        return "high"
    if score_value >= 50:
        return "medium"
    return "low"


def _m2_applicable(doc: Document, m1_firm: str | None, own_channel_firm: str | None) -> bool:
    """Module 2 covers marketing published by investment firms themselves."""
    full = normalize(doc.text)
    promotional = bool(L.PROMO.search(full) or L.PROFIT.search(full) or L.AD_LABEL.search(full))
    return promotional and (own_channel_firm is not None or (m1_firm is None and bool(L.COMPANY_FORM.search(full))))


def analyze(*, url: str, html: str | None = None, text: str | None = None, author: str | None = None,
            title: str = "", register: Register) -> dict:
    doc = parse_html(html, url) if html else parse_text(text or "", url=url, author=author, title=title)
    if author and not doc.author:
        doc.author = author

    m1 = module1(doc, register)
    own_firm = m1.firm if (not m1.applicable and m1.firm) else None

    llm_p, llm_reason = (None, None)
    if llm.enabled() and (L.ADVICE_STRONG.search(normalize(doc.text)) or L.ADVICE_CONTEXT.search(normalize(doc.text))):
        llm_p, llm_reason = llm.advice_probability(doc.visible_text or doc.text)
    m3 = module3(doc, register, llm_p)

    assessments = []
    if m1.applicable:
        assessments.append({
            "module": "m1", "score": m1.score, "level": level(m1.score), "summary": m1.summary,
            "entity": m1.advertiser, "firm": m1.firm, "firm_category": m1.firm_category,
            "signals": [asdict(s) for s in m1.signals], "rules": [],
        })

    if _m2_applicable(doc, m1.firm if m1.applicable else None, own_firm):
        firm_names = [own_firm] if own_firm else [e.name for e in register.find_mentions(doc.text)]
        rules = evaluate(doc, firm_names)
        sc = score(rules)
        failed = [r for r in rules if r.status == FAIL]
        warned = [r for r in rules if r.status == WARN]
        summary = (f"Naruszenia: {', '.join(r.name for r in failed[:3])}" + ("…" if len(failed) > 3 else "")) if failed \
            else ("Uwagi: " + ", ".join(r.name for r in warned[:3])) if warned else "Materiał spełnia kryteria informacji o ryzyku"
        assessments.append({
            "module": "m2", "score": sc, "level": level(sc), "summary": summary,
            "entity": own_firm or (firm_names[0] if firm_names else doc.site_name or doc.author),
            "firm": own_firm, "firm_category": None,
            "signals": [], "rules": [r.to_dict() for r in rules],
        })

    if m3.applicable:
        signals = [asdict(s) for s in m3.signals]
        if llm_reason:
            signals.append({"code": "llm_reason", "label": llm_reason, "weight": 0.0, "evidence": ""})
        assessments.append({
            "module": "m3", "score": m3.score, "level": level(m3.score), "summary": m3.summary,
            "entity": m3.entity, "firm": m3.firm, "firm_category": m3.firm_category,
            "signals": signals, "rules": [],
        })

    visible = doc.visible_text or doc.text
    return {
        "analyzer_version": VERSION,
        "document": {
            "url": url, "title": doc.title, "author": doc.author, "site_name": doc.site_name,
            "language": doc.lang_attr, "text": doc.text[:20000], "excerpt": visible[:600],
            "content_hash": content_hash(doc.text), "simhash": str(simhash(doc.text)),
            "blocks": len(doc.blocks),
        },
        "assessments": assessments,
        "llm": {"enabled": llm.enabled(), "used": llm_p is not None},
    }
