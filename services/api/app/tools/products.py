"""Product master lookups (tool functions for the agents)."""
from __future__ import annotations

import math
import re

from rapidfuzz.distance import DamerauLevenshtein

from ..data import get_repo
from .text import pack_of
from .text import tokens as _tokens

# Words that say nothing about which product is meant: greetings, particles, "is it in stock / where is it"
# phrasing, Javanese/Sundanese-flavoured fillers. Matching is on whole tokens.
_STOPWORDS = set("""
ada adakah yang dong deh sih lah kok nih tuh to toh aja saja banget bgt dulu dlu gimana gmn apa apakah ya yaa
kak kakak pak bapak bu ibu mas mbak om tante halo hai permisi maaf makasih terima kasih tolong plis please
ga gak nggak ngga engga enggak tak tidak belum udah sudah masih masi ready stok stock kosong abis habis ludes
tersedia lorong rak berapa dimana dmn mana di letak letaknya ditaruh taruh
cari nyari mencari nyariin beli butuh perlu minta tanya tanyain coba cek cekin punya jual dijual bisa mau
buat untuk dan atau sama ini itu nya wonten mboten nggih enten onok sampun pripun
ambil mau min punten aya teu atuh lho euy euyy ning ndi sebelah sebungkus sebiji sebuah satu dua tiga
y n k lg lagi dong tuh
gan cepet cepat pagi siang sore malam selamat bang abang mba nanya jam sampai buka bayar parkir qris motor pake
""".split())
# Size adjectives are noise unless the catalog itself uses them (e.g. in synonyms like "santan kecil").
_SIZE_WORDS = {"kecil", "besar", "sedang"}
_TOKEN_SIM = 0.75    # min similarity for two tokens (>=4 chars) to count as the same word
MIN_SCORE = 0.6      # below this a candidate is not returned
CONFIDENT_SCORE = 0.8


_LONG_STOPWORDS = [w for w in _STOPWORDS if len(w) >= 5]
_SIZE = re.compile(r"^(\d+(?:\.\d+)?)(ml|l|kg|g|pcs)?$")
_BASE = {"l": ("ml", 1000.0), "kg": ("g", 1000.0)}  # compare sizes in ml / g


def _base(value: float, unit: str) -> tuple[float, str]:
    unit_to, factor = _BASE.get(unit, (unit, 1.0))
    return value * factor, unit_to


def _size_order(query_tokens: list[str], product: dict) -> tuple[int, float]:
    """Tie-break among equally good name matches by the size the shopper gave: (0 if it fits else 1, then the
    nearest size; smallest first for "kecil", largest first for "besar"). "65" matches 65 ml or 65 g; "1l"
    matches 1000 ml."""
    pack = pack_of(product)
    if pack is None:
        return 1, 0.0
    value, unit = _base(*pack)
    fits, gaps = False, []
    for t in query_tokens:
        m = _SIZE.match(t)
        if not m:
            continue
        q_value = float(m.group(1))
        if m.group(2) is None:  # bare number: compare with the label as printed ("65" vs "65 ml")
            fits |= q_value == pack[0]
            gaps.append(abs(q_value - pack[0]))
        else:
            q_base, q_unit = _base(q_value, m.group(2))
            fits |= (q_base, q_unit) == (value, unit)
            if q_unit == unit:
                gaps.append(abs(q_base - value))
    if gaps:
        return (0 if fits else 1), min(gaps)
    return 1, value if "kecil" in query_tokens else -value if "besar" in query_tokens else 0.0


def _is_filler(tok: str) -> bool:
    """A stopword, or a typo of one ("puntn", "nayri", "wnoten")."""
    if tok in _STOPWORDS:
        return True
    return len(tok) >= 5 and any(DamerauLevenshtein.normalized_similarity(tok, w) >= 0.8 for w in _LONG_STOPWORDS)


def _same_word(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if len(a) < 4 or len(b) < 4 or a[0].isdigit() or b[0].isdigit():
        return 0.0
    if len(a) == len(b) <= 6 and sum(x != y for x, y in zip(a, b)) == 1:
        return 0.0  # one letter replaced in a short word is usually a different word ("merah" vs "murah")
    # Damerau-Levenshtein: a swapped pair of letters ("ubmbu" for "bumbu") counts as one typo
    sim = DamerauLevenshtein.normalized_similarity(a, b)
    return sim if sim >= _TOKEN_SIM else 0.0


class _Index:
    def __init__(self, products: list[dict]):
        self.products = products
        # name, brand, size and the catalog's own synonyms; category words are left out on purpose
        # (they are English/internal labels and only add false matches)
        self.docs = [
            set(_tokens(f"{p['name']} {p['brand']} {p['pack_size']} {' '.join(p.get('synonyms') or [])}"))
            for p in products
        ]
        df: dict[str, int] = {}
        for d in self.docs:
            for t in d:
                df[t] = df.get(t, 0) + 1
        n = len(products)
        self.idf = {t: math.log((n + 1) / (c + 0.5)) + 1 for t, c in df.items()}
        self.unknown_idf = math.log(n + 1) + 1  # a word the catalog has never seen is the strongest signal

    def score(self, query_tokens: list[str], doc: set[str]) -> float:
        total = got = 0.0
        for q in query_tokens:
            w = self.idf.get(q, self.unknown_idf)
            total += w
            got += w * max((_same_word(q, d) for d in doc), default=0.0)
        return got / total if total else 0.0


_cached: tuple[object, _Index] | None = None


def _index() -> _Index:
    """Search index for the active repository (rebuilt when the repository is swapped)."""
    global _cached
    repo = get_repo()
    if _cached is None or _cached[0] is not repo:
        _cached = (repo, _Index(repo.products()))
    return _cached[1]


def search_products(query: str, limit: int = 5) -> dict:
    """Find products in the store catalog that match a shopper's description.

    Pass a short, clean product phrase (e.g. "santan kotak", "minyak goreng 2 liter"), not the whole
    sentence. Each match has a `match_score` between 0 and 1: 0.8 or higher is a confident match; lower
    means ask the shopper to confirm. An empty list means the store does not sell this product.

    Args:
        query: Product name or description as the shopper said it.
        limit: Maximum number of candidates to return.

    Returns:
        A dict with `status` ("ok" or "no_match") and `matches`: list of
        {sku, name, brand, category, pack_size, price_idr, shelf_location, match_score}.
    """
    idx = _index()
    all_tokens = _tokens(query)
    qt = [
        t for t in all_tokens
        # sizes ("65", "100ml", "1l") only order the results (_size_order): a size the catalog lacks must not
        # sink an otherwise good name match below MIN_SCORE
        if not _is_filler(t) and not _SIZE.match(t) and (t not in _SIZE_WORDS or t in idx.idf)
    ]
    if not qt:
        return {"status": "no_match", "matches": [], "query": query}
    scored = [(idx.score(qt, d), p) for d, p in zip(idx.docs, idx.products)]
    scored = [(s, p) for s, p in scored if s >= MIN_SCORE]
    # name match first; among ties, the size the shopper asked for ("65", "1 liter", "kecil")
    scored.sort(key=lambda sp: (-round(sp[0], 2), *_size_order(all_tokens, sp[1]), sp[1]["name"]))
    matches = [
        {
            "sku": p["sku"], "name": p["name"], "brand": p["brand"], "category": p["category"],
            "pack_size": p["pack_size"], "price_idr": p["price_idr"], "shelf_location": p["shelf_location"],
            "match_score": round(s, 2),
        }
        for s, p in scored[: max(1, min(limit, 10))]
    ]
    return {"status": "ok" if matches else "no_match", "matches": matches, "query": query}
