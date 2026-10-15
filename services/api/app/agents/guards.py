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

_UNIT_WORDS = r"(?:pcs|buah|biji|pack|pak|dus|karton|unit|botol|bungkus|sachet|kotak|item|papan|lembar)"
_PRICE = re.compile(r"rp\.?\s*([\d.,]+)", re.I)
_COUNT_UNIT = re.compile(rf"(\d+)\s*{_UNIT_WORDS}\b", re.I)
_COUNT_AFTER_WORD = re.compile(r"\b(?:stok|stock|sisa|tinggal)\b\D{0,15}?(\d+)", re.I)
_INT = re.compile(r"\d+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def claimed_numbers(reply: str) -> set[str]:
    """Prices and stock counts the reply asserts, as digit strings (separators removed)."""
    out = {_digits(m) for m in _PRICE.findall(reply)}
    out |= set(_COUNT_UNIT.findall(reply))
    out |= set(_COUNT_AFTER_WORD.findall(reply))
    out.discard("")
    return out


def numbers_in(text: str) -> set[str]:
    """Every number in a blob of text (tool result JSON, shopper message), separators removed."""
    flat = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", text)
    return set(_INT.findall(flat))


def ungrounded(reply: str, grounded: set[str]) -> set[str]:
    return {n for n in claimed_numbers(reply) if n not in grounded}


def limit_sentences(reply: str, n: int = MAX_SENTENCES) -> str:
    parts = _SENTENCE_END.split(reply.strip())
    return reply.strip() if len(parts) <= n else " ".join(parts[:n])
