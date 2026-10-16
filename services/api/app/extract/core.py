"""Turn one shopper conversation into a demand_signals row (build plan §6.3).

What the shopper asked for (text, sku, normalized_name, category, qty) comes from Gemini when
available, else from the offline catalog matcher. The **outcome** is always decided by rules, not by
the model. On the batch path the rules read the kiosk's replies in the transcript (build plan note:
daily stock_events can't tell a morning purchase from an afternoon stockout); the live path can pass
real-time stock instead via `schema.decide_outcome`.
"""
from __future__ import annotations

import json
import re

from .catalog import STOPWORDS, UNSLANG, Catalog, _stem, _tokens
from .schema import CONFIDENCE_THRESHOLD, Intent, Outcome

# Columns persisted to the demand_signals table (contract §1); `intent` is extracted but not stored.
DEMAND_SIGNALS_COLUMNS = [
    "signal_id", "conversation_id", "sandbox_id", "store_id", "ts", "date", "requested_text",
    "sku", "normalized_name", "category", "outcome", "substitute_sku", "qty", "confidence", "model_version",
]

# Kiosk-reply cues, matched against the agent turns (phrasing from data/sim/conversations.py).
NOT_CARRIED_RE = re.compile(r"belum\s+(kami\s+)?(men)?jual|tidak\s+(kami\s+)?(men)?jual|"
                            r"belum\s+(ada|tersedia|menyediakan)", re.I)
UNAVAIL_RE = re.compile(r"\b(kosong|habis|sold\s*out)\b", re.I)
OFFER_RE = re.compile(r"mau\s+coba", re.I)
ACCEPT_RE = re.compile(r"\b(boleh|ambil)\b|\byang itu\b|\bitu aja\b", re.I)
DECLINE_RE = re.compile(r"\b(nanti|ga jadi|gak jadi|balik lagi|ga usah|gak usah)\b|yaudah ga", re.I)
QTY_RE = re.compile(r"\b(\d{1,2})\b")
# Units that mark a number as a pack size / measure, not a quantity ("65 ml", "10 pcs", "2 L").
QTY_UNIT_RE = re.compile(r"\s*(ml|l|liter|g|gr|gram|kg|kilo|pcs|pack|sachet|sachets|bags|slices|"
                         r"butir|ikat|sisir|lembar|coils|pads|rb|ribu|k)\b", re.I)
LOC_RE = re.compile(r"\b(rak|dimana|di mana|dmn|lorong|sebelah)\b", re.I)


def parse_turns(transcript) -> list[dict]:
    if isinstance(transcript, list):
        return transcript
    try:
        turns = json.loads(transcript)
        return turns if isinstance(turns, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _role_texts(turns: list[dict], role: str) -> list[str]:
    return [str(t.get("text", "")) for t in turns if t.get("role") == role]


def _clean_phrase(text: str) -> str:
    """Normalized_name fallback for items with no SKU match: drop fillers, unslang, de-suffix."""
    toks = [_stem(UNSLANG.get(t, t)) for t in _tokens(text)]
    core = [t for t in toks if t not in STOPWORDS]
    return " ".join(core or toks).strip()


def _parse_qty(text: str) -> int:
    """Quantity the shopper wants (default 1). Numbers followed by a unit are pack sizes, not qty."""
    for m in QTY_RE.finditer(text):
        q = int(m.group(1))
        if 1 <= q <= 20 and not QTY_UNIT_RE.match(text[m.end():]):
            return q
    return 1


def _intent(requested_text: str, unavailable: bool, not_carried: bool) -> Intent:
    if LOC_RE.search(requested_text):
        return Intent.ask_location
    if unavailable or not_carried:
        return Intent.ask_availability
    if re.search(r"\b(beli|mau|pengen|ambil)\b", requested_text, re.I):
        return Intent.buy
    return Intent.ask_availability


def extract_one(conv: dict, cat: Catalog, llm: dict | None = None, model_version: str | None = None) -> dict:
    """One conversation -> one demand_signals dict (contract columns)."""
    turns = parse_turns(conv.get("transcript"))
    shopper = _role_texts(turns, "shopper")
    agent = "\n".join(_role_texts(turns, "agent"))
    requested_text = shopper[0] if shopper else ""
    last_shopper = shopper[-1] if len(shopper) > 1 else ""

    not_carried = bool(NOT_CARRIED_RE.search(agent))
    unavailable = bool(UNAVAIL_RE.search(agent)) and not not_carried

    # --- what the shopper asked for (Gemini, else offline matcher) ---
    if llm is not None:
        prod = cat.get(llm.get("sku"))
        cov, matched = (0.9, 2) if prod else (0.0, 0)
        qty = int(llm.get("qty") or _parse_qty(requested_text))
        model_conf = float(llm.get("confidence") or 0.0)
    else:
        prod, cov, matched = cat.match(requested_text)
        qty = _parse_qty(requested_text)
        model_conf = None

    # --- accepted substitute (only when offered and accepted) ---
    substitute_sku = None
    if unavailable:
        if llm is not None:
            substitute_sku = llm.get("accepted_substitute") or None
        elif OFFER_RE.search(agent) and ACCEPT_RE.search(last_shopper) and not DECLINE_RE.search(last_shopper):
            offer = re.sub(r".*?mau\s+coba\s+", "", agent, flags=re.I | re.S)
            offer = re.split(r"[?.]|\bada di rak\b", offer, maxsplit=1, flags=re.I)[0]
            primary_sku = prod.sku if prod is not None else None
            sub_prod, _, sm = cat.match(offer, exclude={primary_sku} if primary_sku else None)
            substitute_sku = sub_prod.sku if (sub_prod and sm) else None

    # --- outcome by rules (§6.3) ---
    if not_carried:
        outcome, prod = Outcome.not_carried, None            # store does not sell it -> sku null
    elif unavailable and substitute_sku:
        outcome = Outcome.substituted
    elif unavailable:
        outcome = Outcome.out_of_stock
    else:
        outcome = Outcome.purchased

    # --- normalized_name / category ---
    if prod is not None:
        sku, normalized_name, category = prod.sku, prod.normalized_name, prod.category
    else:
        sku = None
        normalized_name = ((llm.get("normalized_name") or "").lower() if llm else "") or _clean_phrase(requested_text)
        category = (llm.get("category") if llm else None) or None

    # --- confidence + low-confidence gate (§6.4) ---
    if model_conf is not None:
        confidence = model_conf
    elif not_carried:
        confidence = 0.85
    elif prod is None:
        confidence = 0.4
    else:
        confidence = round(min(0.98, 0.55 + 0.2 * matched + 0.2 * cov), 2)
    if confidence < CONFIDENCE_THRESHOLD and outcome != Outcome.not_carried:
        outcome = Outcome.low_confidence

    ts = str(conv.get("ts", ""))
    return {
        # one signal per product asked in a chat; the first keeps the plain id (batch chats have only that one)
        "signal_id": f"sig-{conv['conversation_id']}" + (f"-{conv['request']}" if conv.get("request") else ""),
        "conversation_id": conv["conversation_id"],
        "sandbox_id": conv.get("sandbox_id"),
        "store_id": conv.get("store_id"),
        "ts": ts,
        "date": ts[:10],
        "requested_text": requested_text or None,
        "sku": sku,
        "normalized_name": normalized_name or None,
        "category": category,
        "outcome": outcome.value,
        "substitute_sku": substitute_sku,
        "qty": int(qty),
        "confidence": float(confidence),
        "intent": _intent(requested_text, unavailable, not_carried).value,
        "model_version": model_version,
    }
