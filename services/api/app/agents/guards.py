"""Deterministic checks on the shopper agent's replies (no LLM involved).

Rule: stock counts and prices may only come from tool results. We cannot see inside the model, so we check
its output: every price ("Rp 4.500") and stock count ("stok 8", "3 pcs") in the reply must also appear in a
tool result (or in what the shopper said). Anything else is treated as invented and the reply is replaced.
"""
from __future__ import annotations

import re

MAX_SENTENCES = 3
FALLBACK_REPLY = (
    "Maaf kak, aku belum bisa pastiin angka stok atau harganya. Boleh sebut nama produknya sekali lagi?"
)
REFUSAL_REPLY = "Maaf kak, aku cuma bisa bantu cari barang, cek stok, dan harga di toko ini. Mau cari barang apa?"

# Words that exist only in the agent's own instructions and code. A shopper never needs to hear them.
_INTERNALS = re.compile(
    r"aturan mutlak|system prompt|prompt sistem|\b(?:search_products|check_stock|find_alternatives|"
    r"nearest_branch_with_stock|store_id|match_score|stock_status)\b|cara kerja \(selalu panggil tool",
    re.I,
)

_UNIT_WORDS = r"(?:pcs|pc|pieces?|buah|biji|pack|pak|dus|karton|unit|botol|bungkus|sachet|kotak|item|papan|lembar)"
_PRICE = re.compile(r"(?:rp\.?|idr)\s*([\d.,]+)", re.I)
_PRICE_WORD = re.compile(r"([\d.,]*\d)\s*(?:rupiah|perak)\b", re.I)
_PRICE_AFTER_HARGA = re.compile(r"\bharga(?:nya)?\s+([\d][\d.,]*)", re.I)
_PRICE_SCALED = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(rb|ribu|k|jt|juta)\b", re.I)
_COUNT_UNIT = re.compile(rf"(\d+)\s*{_UNIT_WORDS}\b", re.I)
_COUNT_AFTER_WORD = re.compile(r"\b(?:stok|stock|sisa|sisanya|tersisa|tinggal)\b\D{0,15}?(\d+)", re.I)
_COUNT_LAGI = re.compile(r"\b(\d+)\s+lagi\b", re.I)
_INT = re.compile(r"\d+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

_ONES = {"nol": 0, "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5, "enam": 6, "tujuh": 7, "delapan": 8,
         "sembilan": 9}
_WORD_NUMBER = re.compile(
    r"\b(?P<w>(?:se(?:puluh|belas|ratus)|(?:%s)(?:\s+(?:puluh|belas|ratus))?(?:\s+(?:%s))?|sepuluh|sebelas|seratus))"
    rf"\s+{_UNIT_WORDS}\b" % ("|".join(_ONES), "|".join(_ONES)),
    re.I,
)


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def _words_to_int(words: str) -> int | None:
    """'delapan' -> 8, 'dua puluh lima' -> 25, 'sebelas' -> 11, 'seratus' -> 100 (enough for stock counts)."""
    tokens = words.lower().split()
    fixed = {"sepuluh": 10, "sebelas": 11, "seratus": 100}
    if len(tokens) == 1 and tokens[0] in fixed:
        return fixed[tokens[0]]
    total, i = 0, 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t in _ONES and nxt == "belas":
            total, i = total + 10 + _ONES[t], i + 2
        elif t in _ONES and nxt == "puluh":
            total, i = total + 10 * _ONES[t], i + 2
        elif t in _ONES and nxt == "ratus":
            total, i = total + 100 * _ONES[t], i + 2
        elif t in _ONES:
            total, i = total + _ONES[t], i + 1
        elif t == "sepuluh":
            total, i = total + 10, i + 1
        elif t == "sebelas":
            total, i = total + 11, i + 1
        else:
            return None
    return total


def _scaled(raw: str, unit: str) -> str:
    """'4,5' + 'rb' -> '4500'; '2' + 'jt' -> '2000000'."""
    mult = 1_000_000 if unit.lower() in ("jt", "juta") else 1000
    return str(round(float(raw.replace(",", ".")) * mult))


def claimed_prices(reply: str) -> set[str]:
    out = {_digits(m) for m in _PRICE.findall(reply)}
    out |= {_scaled(n, u) for n, u in _PRICE_SCALED.findall(reply)}
    plain = _PRICE_SCALED.sub(" ", reply)  # "4,5rb" is 4500, not also 45
    out |= {_digits(m) for m in _PRICE_WORD.findall(plain)}
    out |= {_digits(m) for m in _PRICE_AFTER_HARGA.findall(plain)}
    out.discard("")
    return out


def claimed_counts(reply: str) -> set[str]:
    out = set(_COUNT_UNIT.findall(reply)) | set(_COUNT_AFTER_WORD.findall(reply)) | set(_COUNT_LAGI.findall(reply))
    for m in _WORD_NUMBER.finditer(reply):
        n = _words_to_int(m.group("w"))
        if n is not None:
            out.add(str(n))
    out.discard("")
    return out


def claimed_numbers(reply: str) -> set[str]:
    """Prices and stock counts the reply asserts, as digit strings (separators removed)."""
    return claimed_prices(reply) | claimed_counts(reply)


def numbers_in(text: str) -> set[str]:
    """Every number in a blob of text (tool result JSON, shopper message), separators removed."""
    flat = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", text)
    return set(_INT.findall(flat))


def ungrounded(reply: str, grounded: set[str], shopper_numbers: set[str] = frozenset()) -> set[str]:
    """Claimed numbers no tool vouches for. What the shopper typed may be echoed back as a quantity ("3 pcs"),
    never as a price: "harganya Rp 1 kan?" must not become "Ya, Rp 1"."""
    bad_prices = {n for n in claimed_prices(reply) if n not in grounded}
    bad_counts = {n for n in claimed_counts(reply) if n not in grounded and n not in shopper_numbers}
    return bad_prices | bad_counts


_STORE_REF = re.compile(r"(?i:radar mart|toko|store|cabang|branch)\s+(?:(?i:radar mart)\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)")
_NOT_A_PLACE = {"Anda", "Kami", "Kita", "Ini", "Itu", "Lain", "Lainnya", "Pertama", "Kedua", "Yang", "Mana", "I", "The",
                "This", "That", "Our", "Your", "Radar", "Mart", "Data", "Manager"}
_INDONESIAN = re.compile(r"\b(?:yang|apa|apakah|berapa|toko|untuk|dan|produk|kenapa|mengapa|bagaimana|minggu|bulan|hari|kamu|anda|tampilkan|tolong|aturan|abaikan|instruksi|sebutkan|jelaskan|saya|aku)\b", re.I)


def known_place_terms(stores: list[dict]) -> set[str]:
    """Lower-case words of every store name, city and id ("radar", "cipete", "jakarta", "s01", ...)."""
    terms: set[str] = set()
    for s in stores:
        for field in ("name", "city", "id"):
            terms |= set(re.findall(r"[a-z0-9]+", str(s.get(field) or "").lower()))
    return terms


def unknown_stores(reply: str, known_terms: set[str]) -> list[str]:
    """Stores the reply names that do not exist ("Radar Mart Bandung"): the agent has no data for them."""
    found = []
    for m in _STORE_REF.finditer(reply):
        words = [w for w in m.group(1).split() if w not in _NOT_A_PLACE]
        if words and words[0].lower() not in known_terms:
            found.append(" ".join(words))
    return list(dict.fromkeys(found))


def unknown_store_reply(names: list[str], store_names: list[str], question: str) -> str:
    listed = ", ".join(store_names)
    if _INDONESIAN.search(question):
        return f"Maaf, aku tidak punya data untuk toko {names[0]}. Data yang ada hanya untuk: {listed}."
    return f"Sorry, I have no data for a store called {names[0]}. I only have data for: {listed}."


_MANAGER_INTERNALS = re.compile(
    r"inventory analyst for the store manager|facts come only from tool|tool guide|views for query_data|"
    r"\b(?:get_recommendations|get_sku_detail|get_assortment_gaps|get_lost_revenue|query_data|forecast_not_ready)\b|"
    r"system prompt|prompt sistem|never invent numbers|evidence id|do not do arithmetic yourself",
    re.I,
)


def leaks_manager_internals(reply: str) -> bool:
    """True when a manager reply recites its instructions or names its tools."""
    return bool(_MANAGER_INTERNALS.search(reply))


def manager_refusal(question: str) -> str:
    if _INDONESIAN.search(question):
        return "Maaf, aku tidak bisa membagikan instruksi internalku. Aku bisa bantu soal stok, rekomendasi pesanan, dan permintaan pembeli."
    return "Sorry, I can't share my internal instructions. I can help with stock, reorder advice and what shoppers ask for."


def leaks_internals(reply: str) -> bool:
    """True when the reply recites instructions or tool names (prompt-extraction attempts)."""
    return bool(_INTERNALS.search(reply))


def limit_sentences(reply: str, n: int = MAX_SENTENCES) -> str:
    parts = _SENTENCE_END.split(reply.strip())
    return reply.strip() if len(parts) <= n else " ".join(parts[:n])
