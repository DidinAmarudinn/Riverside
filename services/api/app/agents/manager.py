"""Store-manager agent (ADK): explains reorder advice and answers questions over the BigQuery views.

Facts come from tools only. Each tool returns evidence items; the `after_tool_callback` numbers them E1, E2, ...
(unique per conversation) and the model cites them as [E#]. The API returns the cited evidence as `citations`
so the UI can link a claim to its SKU/date/quote. Numbers in the reply that appear in no tool result are
reported as `unverified_numbers` instead of being silently trusted.
"""
from __future__ import annotations

import json
import logging
import re

from google.adk.agents import Agent
from google.genai import types

from ..config import settings
from ..tools.analytics import get_lost_revenue, get_recommendations, get_sku_detail
from ..tools.bq import get_runner, query_data
from ..tools.gaps import get_assortment_gaps
from . import guards
from .llm import reply_config, thinking_planner

log = logging.getLogger(__name__)

INSTRUCTION = """You are Demand Radar, an inventory analyst for the store manager of Radar Mart (grocery). \\
Reply in the language the manager wrote the question in (English or Bahasa Indonesia), whatever language \
the data, product names or shopper quotes are in. Be concise: at most 5 short \\
sentences or a list of at most 5 items. When asked what to do, end with one clear recommendation.

The latest user message ends with a "(context: ...)" line giving the store and, if any, the SKU on screen. \\
Use that store_id unless the manager asks about another store or all stores.

Rules:
- Facts come ONLY from tool results. Never invent numbers, SKUs, dates, prices or shopper quotes. If a tool \\
returns nothing useful, say so.
- Do not do arithmetic yourself. For totals, averages or comparisons that no tool returns, write one SQL \\
query for query_data (SELECT over the views) and report its result.
- Every number or claim must be followed by the evidence id it came from, written like [E3]. Use the `id` \\
fields in the tools' `evidence` lists. Quote shopper requests verbatim when they support the point.
- Forecast A uses POS sales only; it is blind to demand lost while a shelf was empty (POS shows 0 sales). \\
Forecast B adds unmet demand captured from shopper conversations. When both exist, explain the gap between \\
them in plain words. Never state a recommended order quantity that a tool did not return.
- Product names in the data are in Bahasa Indonesia ("coconut milk" is "santan", "eggs" is "telur"). If a \
product lookup is ambiguous, pick the candidate with the most unmet demand and say which one you chose.
- If a tool reports status "forecast_not_ready" or forecast_available=false, tell the manager that forecasts \\
and recommended quantities are not available yet, and use only observed facts (empty shelves, days out of \\
stock, unmet shopper requests).
- "Today" is the latest day in the data; for "yesterday" call get_lost_revenue with days_ago=1.
- Write money as Rp 1.931.750 (dot as thousands separator).

Tool guide: get_recommendations (what is at risk / what to order), get_sku_detail (one product, accepts a \\
SKU code or a name), get_assortment_gaps (what shoppers ask for that the store does not sell), \\
get_lost_revenue (revenue lost to stockouts), query_data (anything else, SQL over the views).
"""

_MARKER = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")   # [E3] or [E1, E2]
_ID = re.compile(r"E\d+")
_MIN_DIGITS = 2   # single digits ("top 3", "2 sizes") are not worth flagging


# -- callbacks ------------------------------------------------------------------------------------
def _record_tool_result(tool, args, tool_context, tool_response):
    """Number the evidence, remember what the tool said (for number checks) and what was called."""
    state = tool_context.state
    seq = int(state.get("evidence_seq", 0))
    store = dict(state.get("evidence", {}))
    numbered = []
    for item in tool_response.get("evidence") or []:
        seq += 1
        item = {**item, "id": f"E{seq}"}
        store[item["id"]] = item
        numbered.append(item)
    tool_response["evidence"] = numbered
    state["evidence_seq"], state["evidence"] = seq, store
    state["turn_evidence_ids"] = list(state.get("turn_evidence_ids", [])) + [e["id"] for e in numbered]

    grounded = set(state.get("grounded", [])) | guards.numbers_in(json.dumps(tool_response, ensure_ascii=False))
    state["grounded"] = sorted(grounded)
    calls = list(state.get("turn_tool_calls", []))
    calls.append({"name": tool.name, "args": dict(args), "status": tool_response.get("status")})
    state["turn_tool_calls"] = calls
    return tool_response


def _check_reply(callback_context, llm_response):
    content = llm_response.content
    if not content or not content.parts or any(p.function_call for p in content.parts):
        return None
    text = "".join(p.text or "" for p in content.parts if not p.thought).strip()
    if not text:
        return None
    state = callback_context.state
    allowed = set(state.get("grounded", []))
    if callback_context.user_content and callback_context.user_content.parts:
        allowed |= guards.numbers_in(" ".join(p.text or "" for p in callback_context.user_content.parts))
    evidence = state.get("evidence", {})
    text = _MARKER.sub(lambda m: _keep_known(m.group(1), evidence), text).replace("  ", " ")  # drop invented ids
    unverified = sorted(n for n in guards.numbers_in(_MARKER.sub("", text)) - allowed if len(n) >= _MIN_DIGITS)
    if unverified:
        log.warning("manager reply has numbers no tool returned: %s", unverified)
    state["turn_unverified"] = unverified
    state["turn_reply"] = text
    llm_response.content = types.Content(role="model", parts=[types.Part(text=text)])
    return llm_response


def _keep_known(ids: str, evidence: dict) -> str:
    """'[E1, E9]' with only E1 known -> '[E1]'; none known -> ''."""
    known = [i for i in _ID.findall(ids) if i in evidence]
    return f"[{', '.join(known)}]" if known else ""


def finish_turn(callback_context):
    """Resolve [E#] markers into citations and reset the per-turn accumulators."""
    state = callback_context.state
    evidence = state.get("evidence", {})
    reply = state.get("turn_reply", "")
    cited = [i for i in dict.fromkeys(i for grp in _MARKER.findall(reply) for i in _ID.findall(grp)) if i in evidence]
    if not cited:  # the model forgot the markers: fall back to everything it looked at this turn
        cited = [i for i in state.get("turn_evidence_ids", []) if i in evidence]
    state["last_turn"] = {
        "citations": [evidence[i] for i in cited],
        "unverified_numbers": state.get("turn_unverified", []),
        "tool_calls": state.get("turn_tool_calls", []),
    }
    state["turn"] = int(state.get("turn", 0)) + 1
    for key in ("turn_tool_calls", "turn_evidence_ids", "turn_unverified"):
        state[key] = []
    state["turn_reply"] = ""
    return None


_schema_text: str | None = None


def _instruction(_ctx) -> str:
    """Instruction plus the live column list of the queryable views (read from BigQuery metadata once), so the
    model writes valid SQL the first time instead of guessing column names."""
    global _schema_text
    if _schema_text is None:
        try:
            cols = get_runner().view_columns()
            _schema_text = "\n\nViews for query_data and their columns:\n" + "\n".join(
                f"- {view}({', '.join(c)})" for view, c in cols.items())
        except Exception:  # no BigQuery metadata (tests, offline): the model gets the error text on bad SQL
            log.warning("could not read view schemas for the manager instruction", exc_info=True)
            return INSTRUCTION
    return INSTRUCTION + _schema_text


def build_manager_agent(model=None) -> Agent:
    return Agent(
        name="manager_agent",
        model=model or settings.gemini_model,
        instruction=_instruction,
        tools=[get_recommendations, get_sku_detail, get_assortment_gaps, get_lost_revenue, query_data],
        generate_content_config=reply_config(temperature=0.2),
        planner=thinking_planner(),
        after_tool_callback=_record_tool_result,
        after_model_callback=_check_reply,
        after_agent_callback=finish_turn,
    )


manager_agent = build_manager_agent()
