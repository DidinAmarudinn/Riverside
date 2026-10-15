"""Text helpers shared by the product tools: tokenisation, pack-size parsing, product 'kind' tokens."""
from __future__ import annotations

import re

# Spelling/slang normalisation applied to queries and catalog text alike.
SPELLING = {"mie": "mi", "telor": "telur", "cabe": "cabai", "saos": "saus", "santen": "santan", "migor": "minyak goreng"}
UNITS = {"liter": "l", "ltr": "l", "lt": "l", "gram": "g", "gr": "g", "kilo": "kg", "kilogram": "kg"}
_NYA = re.compile(r"\b(\w{3,}?)nya\b")  # "stoknya" / "50gnya" -> "stok" / "50g"
_QTY_UNIT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|liter|ltr|lt|l|kg|kilogram|kilo|gram|gr|g|pcs)\b")
_SIZE_TOKEN = re.compile(r"^\d+(?:\.\d+)?(?:ml|l|kg|g|pcs)?$")
_PACK = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)\s*$")


def tokens(text: str) -> list[str]:
    text = _NYA.sub(r"\1", text.lower().replace("&", " ").replace("_", " "))
    text = _QTY_UNIT.sub(lambda m: m.group(1).replace(",", ".") + UNITS.get(m.group(2), m.group(2)), text)
    out: list[str] = []
    for tok in re.findall(r"[a-z0-9.]+", text):
        tok = tok.strip(".")
        if tok:
            out.extend(SPELLING.get(tok, tok).split())
    return out


def pack_of(product: dict) -> tuple[float, str] | None:
    """(value, unit) from a label like '65 ml'; None when it cannot be parsed."""
    m = _PACK.match(str(product.get("pack_size", "")))
    if not m:
        return None
    return float(m.group(1).replace(",", ".")), UNITS.get(m.group(2).lower(), m.group(2).lower())


def kind_tokens(product: dict) -> set[str]:
    """What the product *is* (e.g. {santan, kotak}): name words minus brand and size."""
    brand = set(tokens(product.get("brand", "")))
    return {t for t in tokens(product["name"]) if t not in brand and not _SIZE_TOKEN.match(t)}
