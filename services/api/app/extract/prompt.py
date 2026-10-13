"""Prompt for turning a shopper conversation into demand signals."""

SYSTEM_PROMPT = """You extract demand signals from grocery-store conversations written in informal \
Bahasa Indonesia (slang, typos, descriptions without brand names).

For every product the shopper wanted, return one item:
- sku: the best match from the CANDIDATES list, or null if the store does not sell it
- outcome: bought | out_of_stock | not_stocked | substituted
- match_confidence: 0..1
Ignore chit-chat that is not about a product. Never invent SKUs that are not in CANDIDATES."""


def build_user_prompt(transcript: str, candidates: list[dict]) -> str:
    lines = "\n".join(f"{c['sku']} | {c['name']} | {c['category']}" for c in candidates)
    return f"CANDIDATES:\n{lines}\n\nCONVERSATION:\n{transcript}"
