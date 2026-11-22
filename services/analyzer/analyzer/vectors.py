"""Lightweight text embeddings without heavy ML dependencies.

A hashing vectorizer over word unigrams/bigrams and character 4-grams gives a
fixed-size sparse representation. It is used for near-duplicate checks and for
a prototype (nearest-centroid) classifier that complements the rule lexicons
— e.g. telling an advisory *offer* apart from an *educational* article.
A transformer model (BERT / Gemma via Ollama) can replace `embed()` without
touching the callers.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from .preprocess import normalize

DIM = 2**18


def _h(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(), "big") % DIM


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%]+", normalize(text))


def embed(text: str) -> dict[int, float]:
    toks = tokens(text)
    feats: Counter[int] = Counter()
    for t in toks:
        feats[_h("w:" + t)] += 1.0
    for a, b in zip(toks, toks[1:]):
        feats[_h(f"b:{a}_{b}")] += 1.0
    joined = " ".join(toks)
    for i in range(len(joined) - 3):
        feats[_h("c:" + joined[i : i + 4])] += 0.3
    # sublinear tf + L2 norm
    vec = {k: 1 + math.log(v) for k, v in feats.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {k: v / norm for k, v in vec.items()}


def cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def centroid(texts: list[str]) -> dict[int, float]:
    acc: Counter[int] = Counter()
    for t in texts:
        for k, v in embed(t).items():
            acc[k] += v
    norm = math.sqrt(sum(v * v for v in acc.values())) or 1.0
    return {k: v / norm for k, v in acc.items()}


class PrototypeClassifier:
    """Nearest-centroid classifier: P(positive) from cosine margin to two prototypes."""

    def __init__(self, positive: list[str], negative: list[str], temperature: float = 12.0):
        self.pos = centroid(positive)
        self.neg = centroid(negative)
        self.t = temperature

    def predict(self, text: str) -> float:
        v = embed(text)
        margin = cosine(v, self.pos) - cosine(v, self.neg)
        return 1 / (1 + math.exp(-self.t * margin))


ADVISORY = PrototypeClassifier(
    positive=[
        "oferujemy indywidualne doradztwo inwestycyjne i rekomendacje zakupu akcji dopasowane do twojego profilu",
        "family office zarządzanie majątkiem rodzinnym dobór portfela inwestycji konsultacja z doradcą",
        "wealth management stworzymy dla ciebie spersonalizowaną strategię inwestycyjną i powiemy co kupić",
        "płatna grupa vip sygnały kupna i sprzedaży akcji kryptowalut codziennie rekomendacje transakcji",
        "umów konsultację inwestycyjną przeanalizujemy twój portfel i zarekomendujemy fundusze etf obligacje",
        "investment consulting personalised portfolio recommendations buy sell advice for private clients",
    ],
    negative=[
        "artykuł edukacyjny wyjaśnia czym są obligacje skarbowe i jak działa inflacja nie stanowi porady",
        "kurs dla początkujących podstawy giełdy słowniczek pojęć materiał ma charakter wyłącznie edukacyjny",
        "wiadomości rynkowe indeks wig20 zamknął się wzrostem komentarz ekonomistów dane makro",
        "poradnik jak sprawdzić czy firma ma zezwolenie knf lista ostrzeżeń publicznych",
        "kalkulator procentu składanego oszczędzanie budżet domowy fundusz awaryjny",
        "our blog explains diversification and risk in general terms this is not investment advice",
    ],
)
