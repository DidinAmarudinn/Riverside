"""Product catalog for signal extraction (build plan §6.2).

The catalog holds only `is_carried = true` products (build plan note): items the store does not
sell must come back as `sku = null` so the outcome rules can label them `not_carried`. It drives both
the Gemini prompt (a compact `sku | name | synonyms` list) and an offline fuzzy matcher used by the
template extractor and as a fallback when Gemini is unavailable.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

try:  # optional: faster/better fuzzy matching
    from rapidfuzz import fuzz as _rf  # type: ignore
except Exception:  # pragma: no cover - fallback path
    _rf = None

# data/product_master.csv, resolved from this file (…/services/api/app/extract/catalog.py).
DEFAULT_MASTER = Path(__file__).resolve().parents[4] / "data" / "product_master.csv"

_WORD = re.compile(r"[a-z0-9]+")
_SUFFIX = re.compile(r"(nya|nih)$")

# Filler/scaffolding words that are not part of a product name (mirrors conversations.py phrasing).
STOPWORDS = {
    "kak", "mas", "mba", "mbak", "bang", "gan", "min", "halo", "hai", "permisi", "pagi", "sore", "malam",
    "ada", "ga", "gak", "ngga", "nggak", "engga", "masih", "stok", "stoknya", "ready", "kosong", "habis",
    "nyari", "cari", "mau", "beli", "tanya", "lagi", "jual", "di", "rak", "mana", "dimana", "dmn", "ya",
    "yaa", "dong", "nih", "deh", "plis", "cepet", "yg", "yang", "aja", "buat", "punya", "ngga", "jadi",
}
UNSLANG = {"yg": "yang", "gak": "tidak", "ga": "tidak", "dmn": "dimana", "migor": "minyak goreng",
           "bawmer": "bawang merah", "bawput": "bawang putih"}


@dataclass
class Product:
    sku: str
    name: str
    brand: str
    category: str
    normalized_name: str
    synonyms: tuple[str, ...]
    syn_tokens: tuple[tuple[tuple[str, ...], str], ...]  # (tokens, original synonym)
    size_tokens: frozenset[tuple[float, str]]            # e.g. {(65.0, "ml")} from pack_size
    size_value: float                                    # numeric size in base units, for ordering


_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|l|liter|gr|gram|g|kg|kilo)\b", re.I)
_UNIT_CANON = {"liter": "l", "l": "l", "gram": "g", "gr": "g", "g": "g", "kg": "kg", "kilo": "kg", "ml": "ml"}
_UNIT_SCALE = {"ml": 1.0, "l": 1000.0, "g": 1.0, "kg": 1000.0}
_SIZE_WORD_RE = re.compile(r"\b(kecil|sedang|besar|jumbo)\b", re.I)


def parse_sizes(text: str) -> set[tuple[float, str]]:
    """All (number, canonical-unit) sizes mentioned in a string ('500gr' -> {(500.0, 'g')})."""
    out = set()
    for num, unit in _SIZE_RE.findall(text):
        out.add((float(num), _UNIT_CANON[unit.lower()]))
    return out


def _size_value(sizes: set[tuple[float, str]]) -> float:
    return max((n * _UNIT_SCALE.get(u, 1.0) for n, u in sizes), default=0.0)


def _size_word(text: str) -> str | None:
    m = _SIZE_WORD_RE.search(text)
    if not m:
        return None
    return "besar" if m.group(1).lower() == "jumbo" else m.group(1).lower()


def normalize_name(name: str, brand: str) -> str:
    """Lower-case product name with the brand removed and whitespace collapsed.

    Must match the normalized_name produced by sql/05_bootstrap_signals.sql so signals group the same
    way whether they came from the bootstrap seed or the extractor.
    """
    core = name if not brand else name.replace(brand, "")
    return re.sub(r"\s+", " ", core).strip().lower()


def _tokens(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def _stem(t: str) -> str:
    return _SUFFIX.sub("", t) if len(t) > 5 else t


def _ratio(a: str, b: str) -> float:
    return _rf.ratio(a, b) / 100.0 if _rf is not None else SequenceMatcher(None, a, b).ratio()


def _token_match(syn_tok: str, text_toks: list[str]) -> float:
    best = 0.0
    for t in text_toks:
        if t == syn_tok:
            return 1.0
        if len(syn_tok) >= 4 and len(t) >= 4:
            best = max(best, _ratio(syn_tok, t))
    return best if best >= 0.8 else 0.0


class Catalog:
    def __init__(self, products: list[dict]):
        self.carried: list[Product] = []
        for p in products:
            if not _as_bool(p.get("is_carried")):
                continue
            brand = (p.get("brand") or "").strip()
            synonyms = tuple(s for s in (p.get("synonyms") or "").split("|") if s)
            sizes = parse_sizes(p.get("pack_size", ""))
            self.carried.append(Product(
                sku=p["sku"], name=p["name"], brand=brand, category=p.get("category", ""),
                normalized_name=normalize_name(p["name"], brand), synonyms=synonyms,
                syn_tokens=tuple((tuple(_tokens(s)), s) for s in synonyms if s),
                size_tokens=frozenset(sizes), size_value=_size_value(sizes),
            ))
        self._by_sku = {p.sku: p for p in self.carried}

    def get(self, sku: str | None) -> Product | None:
        return self._by_sku.get(sku) if sku else None

    def match(self, text: str, exclude: set[str] | None = None) -> tuple[Product | None, float, int]:
        """Best (product, coverage, n_matched_tokens) for a shopper phrase, or (None, 0, 0).

        Family is chosen by synonym-token coverage; the size variant is then disambiguated by any
        size the shopper stated ("500 g", "2 L") or a size word ("kecil"/"besar"). Pass `exclude` to
        skip SKUs (e.g. the primary item, when matching an offered substitute).
        """
        exclude = exclude or set()
        toks = [_stem(UNSLANG.get(t, t)) for t in _tokens(text)]
        toks = [t for t in toks if t not in STOPWORDS] or toks

        scored: list[tuple[Product, float, int]] = []
        for p in self.carried:
            if p.sku in exclude:
                continue
            best_cov, best_matched = 0.0, 0
            for syn_toks, _syn in p.syn_tokens:
                if not syn_toks:
                    continue
                scores = [_token_match(st, toks) for st in syn_toks]
                matched = sum(1 for s in scores if s > 0)
                if matched and (matched, sum(scores) / len(syn_toks)) > (best_matched, best_cov):
                    best_matched, best_cov = matched, sum(scores) / len(syn_toks)
            if best_matched:
                scored.append((p, best_cov, best_matched))
        if not scored:
            return (None, 0.0, 0)

        # Keep the family/families that matched the most specific synonym tokens.
        top = max(m for _, _, m in scored)
        cands = [s for s in scored if s[2] == top]

        req_sizes = parse_sizes(text)
        if req_sizes:
            sized = [s for s in cands if req_sizes & s[0].size_tokens]
            if sized:
                cands = sized
        else:
            word = _size_word(text)
            if word and len(cands) > 1:
                order = sorted(cands, key=lambda s: s[0].size_value)
                return order[0] if word == "kecil" else order[-1] if word == "besar" else order[len(order) // 2]

        cands.sort(key=lambda s: (-s[1], s[0].sku))
        return cands[0]

    def prompt_lines(self) -> str:
        """Compact catalog for the Gemini prompt: sku | normalized_name | category | synonyms."""
        return "\n".join(
            f"{p.sku} | {p.normalized_name} | {p.category} | {', '.join(p.synonyms[:8])}"
            for p in self.carried
        )


def _as_bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def load_products(master_path: Path | None = None) -> list[dict]:
    with open(master_path or DEFAULT_MASTER, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=4)
def load_catalog(master_path: str | None = None) -> Catalog:
    return Catalog(load_products(Path(master_path) if master_path else None))
