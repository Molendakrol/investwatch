"""Matching text against the register of authorised investment firms."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .preprocess import normalize

LEGAL_SUFFIX = re.compile(
    r"\b(s\.?\s?a\.?|sp\.?\s?z\s?o\.?\s?o\.?|spolka akcyjna|spolka z ograniczona odpowiedzialnoscia|ltd\.?|limited|gmbh|"
    r"s\.?p\.?a\.?|plc|n\.?v\.?|a\.?s\.?|ag|se|oddzial w polsce|branch in poland)\b"
)
GENERIC = {"dom", "maklerski", "dom maklerski", "bank", "investment", "capital", "management", "invest", "polska", "s", "a",
           "ext", "trade", "trading", "markets", "finance", "group", "global", "europe", "partners", "securities"}


def key(name: str) -> str:
    """Canonical matching key: normalized, without legal-form suffixes and punctuation."""
    n = normalize(name)
    n = LEGAL_SUFFIX.sub(" ", n)
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return re.sub(r"\s+", " ", n).strip()


@dataclass
class RegisterEntry:
    name: str
    category: str  # dom_maklerski | bank | oddzial | transgraniczna | demo
    scope: str = ""
    source_url: str = ""

    @property
    def authorised_for_advice(self) -> bool:
        # In the UKNF register "Zakres działalności" uses numbered items; item 5
        # (art. 69 ust. 2 pkt 5 uobrot) is investment advice. Banks / notified
        # foreign firms carry their scope in the notification — treated as authorised.
        if self.category in ("bank", "oddzial", "transgraniczna"):
            return True
        items = {s.strip() for s in re.split(r"[,;\s]+", self.scope) if s.strip()}
        return "5" in items or "doradztwo" in self.scope.lower()


class Register:
    def __init__(self, entries: list[RegisterEntry]):
        self.entries = entries
        self._index: list[tuple[str, RegisterEntry]] = []
        for e in entries:
            k = key(e.name)
            if len(k) >= 3 and k not in GENERIC:
                self._index.append((k, e))
        # longest keys first so "dom maklerski nordwisla" wins over "nordwisla"
        self._index.sort(key=lambda kv: -len(kv[0]))

    def __len__(self) -> int:
        return len(self.entries)

    def find_mentions(self, text: str) -> list[RegisterEntry]:
        hay = " " + re.sub(r"[^a-z0-9 ]+", " ", normalize(text)) + " "
        hay = re.sub(r"\s+", " ", hay)
        found: list[RegisterEntry] = []
        seen: set[str] = set()
        for k, e in self._index:
            if f" {k} " in hay and e.name not in seen:
                found.append(e)
                seen.add(e.name)
        return found

    def lookup(self, name: str) -> RegisterEntry | None:
        k = key(name)
        if not k:
            return None
        for kk, e in self._index:
            if kk == k or (len(k) > 6 and (k in kk or kk in k)):
                return e
        return None


# Fictional firms used by the synthetic demo pages. They never collide with
# real register names and are tagged as "demo" everywhere in the UI.
DEMO_ENTRIES = [
    RegisterEntry("Dom Maklerski Nordwisła S.A.", "demo", "1, 2, 3, 4, 5, 6", "demo"),
    RegisterEntry("Vistula Invest Dom Maklerski S.A.", "demo", "1, 4, 5, 6", "demo"),
    RegisterEntry("Baltic Capital Markets Ltd", "demo", "transgraniczna (UE)", "demo"),
    RegisterEntry("Mazowiecki Dom Inwestycyjny S.A.", "demo", "1, 4, 6", "demo"),
]
