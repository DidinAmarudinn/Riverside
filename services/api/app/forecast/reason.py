"""`reason_text` for a recommendation row (build plan 7.7): one or two sentences, numbers only from the data.

Gemini writes the sentence from the row's own numbers and the calendar context. Every number in its answer must appear
in that input; otherwise (or on any error) a deterministic template built from the same numbers is used instead.
"""
from __future__ import annotations

import json
import re

import pandas as pd

from ..agents.guards import numbers_in

SYSTEM = (
    "You write the explanation shown under a grocery reorder recommendation, for a store manager. Write exactly one or "
    "two short sentences in English and start with the product name (never with 'Reason'). First say the situation "
    "using on_hand and forecast_b_next_7_days. If forecast_a_next_7_days is given, explain that the POS-only forecast A "
    "is much lower because the shelf was empty while shoppers kept asking (unmet_requests_last_7_days times), and say "
    "what A would order (recommended_order_a). End with the action, worded as given in 'action'. Use only numbers that "
    "appear in the JSON, never compute or invent new ones. Mention the calendar only if a 'calendar' field is given, and only as the upcoming event it describes."
)

_LABEL = {"stockout_risk": "stockout risk", "unmet_spike": "unmet-demand spike", "overstock": "overstock",
          "reorder": "reorder"}


def _round(v: float) -> float | int:
    """Whole units from 10 up, one decimal below: the text quotes exactly what the model was given."""
    return int(round(v)) if abs(v) >= 10 else round(float(v), 1)


def facts_for(row: dict, name: str, context: dict) -> dict:
    """The only data the text may use."""
    fa, fb = row["forecast_a_7d"], row["forecast_b_7d"]
    out = {"product": name, "risk": _LABEL.get(row["risk_type"], row["risk_type"]), "on_hand": row["on_hand"],
           "forecast_b_next_7_days": _round(fb), "recommended_order_b": row["recommended_qty_b"],
           "action": f"order {row['recommended_qty_b']} units" if row["recommended_qty_b"] > 0 else "hold the order",
           "unmet_requests_last_7_days": row["unmet_7d"], "lost_revenue_idr": row["lost_revenue_idr"], **context}
    if fb > 0 and (fb - fa) >= max(3.0, 0.2 * fb):   # forecast A is materially lower: that gap is the story
        out["forecast_a_next_7_days"] = _round(fa)
        out["recommended_order_a"] = row["recommended_qty_a"]
    return out


def _num(v) -> str:
    return f"{v:,.0f}".replace(",", ".") if float(v) == int(v) or abs(v) >= 100 else f"{v:.1f}"


def template_reason(f: dict) -> str:
    """Deterministic fallback: states the facts of the row and nothing else."""
    risk = f["risk"]
    if risk == "stockout risk":
        text = (f"{f['product']}: {_num(f['on_hand'])} on hand against a forecast of {_num(f['forecast_b_next_7_days'])} "
                f"units over the next 7 days, so {f['action']}.")
        if "forecast_a_next_7_days" in f:
            text += (f" POS-only forecast A sees {_num(f['forecast_a_next_7_days'])} units and would order "
                     f"{_num(f['recommended_order_a'])}; shoppers asked {_num(f['unmet_requests_last_7_days'])} times "
                     f"while the shelf was empty.")
        return text
    if risk == "unmet-demand spike":
        return (f"{f['product']}: {_num(f['unmet_requests_last_7_days'])} unmet requests in the last 7 days, more than "
                f"twice the week before. Forecast B expects {_num(f['forecast_b_next_7_days'])} units over the next 7 days; "
                f"order {_num(f['recommended_order_b'])}.")
    if risk == "overstock":
        return (f"{f['product']}: {_num(f['on_hand'])} on hand covers far more than the {_num(f['forecast_b_next_7_days'])} "
                f"units forecast for the next 7 days; hold the order.")
    return (f"{f['product']}: forecast B expects {_num(f['forecast_b_next_7_days'])} units over the next 7 days with "
            f"{_num(f['on_hand'])} on hand; order {_num(f['recommended_order_b'])}.")


def numbers_grounded(text: str, f: dict) -> bool:
    """Every number in `text` must appear in the facts (or be a small count word like 'one' written as a digit)."""
    allowed = numbers_in(json.dumps(f, ensure_ascii=False)) | {"7", "1", "2"}  # "7 days", "two sentences", "A"/"B" are not digits
    return numbers_in(text) <= allowed


def llm_reason(client, model: str, f: dict) -> str | None:
    from google.genai import types

    cfg = types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.2, max_output_tokens=160,
                                      thinking_config=types.ThinkingConfig(thinking_budget=0))
    try:
        resp = client.models.generate_content(model=model, contents=json.dumps(f, ensure_ascii=False), config=cfg)
    except Exception:
        return None
    text = re.sub(r"\s+", " ", (resp.text or "")).strip()
    if not text or len(text) > 420 or text.lower().startswith("reason") or not numbers_grounded(text, f):
        return None
    if f["recommended_order_b"] > 0 and str(f["recommended_order_b"]) not in text:   # the action must be in the text
        return None
    return text


def add_reason_text(df: pd.DataFrame, names: dict[str, str], context: dict, client=None, model: str = "",
                    workers: int = 6) -> tuple[pd.DataFrame, dict[str, int]]:
    """Fill `reason_text` for every flagged row; returns the frame and counts of how each text was produced."""
    from concurrent.futures import ThreadPoolExecutor

    out = df.copy()
    idx = out.index[out["risk_type"].notna()].tolist()
    facts = {i: facts_for(out.loc[i].to_dict(), names.get(out.at[i, "sku"], out.at[i, "sku"]), context) for i in idx}

    def one(i: int) -> tuple[int, str, str]:
        text = llm_reason(client, model, facts[i]) if client is not None else None
        return (i, text, "gemini") if text else (i, template_reason(facts[i]), "template")

    stats = {"gemini": 0, "template": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, text, how in pool.map(one, idx):
            out.at[i, "reason_text"] = text
            stats[how] += 1
    return out, stats
