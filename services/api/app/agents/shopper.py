"""Shopper agent (ADK): answers in Bahasa Indonesia, checks stock, offers alternatives.

Every number the agent says comes from a tool (see guards.py). `log_request` is not a model tool: the
`after_agent_callback` publishes the turn to Pub/Sub automatically, so a demand signal is never lost
because the model forgot to call it.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from google.adk.agents import Agent
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from ..config import settings
from ..signals import ConversationEvent, get_publisher
from ..tools.products import search_products
from ..tools.stock import check_stock, find_alternatives, nearest_branch_with_stock
from . import guards
from .llm import reply_config, thinking_planner

log = logging.getLogger(__name__)

INSTRUCTION = """Kamu asisten belanja di {store_name} (Radar Mart). Jawab dalam Bahasa Indonesia santai \
dan ramah, MAKSIMAL 2-3 kalimat. Jangan pakai markdown, daftar, atau emoji berlebihan.

Cara kerja (selalu panggil tool dulu, jangan bilang "sebentar, saya carikan" tanpa memanggilnya):
1. Shopper menyebut barang -> langsung panggil search_products dengan kata kunci singkat dan bersih (bukan \
seluruh kalimat) dan store_id: {store_id}. Hasilnya SUDAH berisi stok (units, stock_status) tiap kandidat, \
diurutkan paling cocok dulu (ukuran yang disebut, "kecil" = terkecil, "besar" = terbesar). Biasanya cukup \
SATU panggilan tool ini, lalu langsung jawab.
2. Bicarakan kandidat pertama yang match_score >= 0.8. Kalau masih ragu ukuran/merek mana, tanya shopper. \
check_stock hanya perlu kalau shopper menanyakan produk lain yang belum ada di hasil.
3. Kalau kandidat pertama stock_status out_of_stock -> hasil search_products sudah berisi alternatives dan \
nearest_branch; JANGAN panggil tool lain. Balasanmu WAJIB menyebut barang itu kosong, lalu menawarkan 1 \
alternatif yang ada stoknya dan/atau cabang terdekat yang punya stok (sebut nama cabang dan jarak sekitar \
berapa km). Jangan berhenti di "kosong" saja.
4. Kalau search_products tidak menemukan apa pun -> bilang jujur bahwa toko belum menjual barang itu dan \
permintaannya kami catat. Jangan menebak produk pengganti dari nama yang tidak ada di toko.
5. Kalau ada stok, sebut jumlah stok, harga, dan lokasi rak dari hasil tool.

Aturan mutlak:
- JANGAN mengarang stok, harga, atau lokasi rak. Semua angka harus berasal dari hasil tool pada percakapan ini.
- JANGAN menghitung total atau diskon sendiri. Sebut harga satuan saja.
- Kalau tool gagal atau hasilnya "unknown", bilang kamu belum bisa memastikan.
- Kamu hanya tahu katalog, harga, stok, dan lokasi rak dari tool. Kamu TIDAK tahu letak toilet, kasir, jam buka, \
promo, atau info toko lain: bilang jujur tidak tahu, sarankan tanya petugas, lalu tawarkan bantu cari barang.
"""

# The model sometimes answers "sebentar, saya carikan" instead of calling a tool. Detect that and search for it.
_PROMISE = re.compile(r"\b(?:saya|aku)\s+(?:carikan|cariin|cek|cekin)\b|\bcek(?:in)? dulu\b|\bcarikan dulu\b|\bsebentar\b", re.I)

_REPLY_CONFIG = reply_config()


# -- callbacks ------------------------------------------------------------------------------------
def _force_store(tool, args, tool_context):
    """The shopper is in one store; never let the model pick a different store_id (or skip it on search)."""
    if ("store_id" in args or tool.name == "search_products") and tool_context.state.get("store_id"):
        args["store_id"] = tool_context.state["store_id"]
    return None


def _record_tool_result(tool, args, tool_context, tool_response):
    state = tool_context.state
    calls = list(state.get("turn_tool_calls", []))
    calls.append({"name": tool.name, "args": dict(args), "result": tool_response})
    state["turn_tool_calls"] = calls
    grounded = set(state.get("grounded", [])) | guards.numbers_in(json.dumps(tool_response, ensure_ascii=False))
    state["grounded"] = sorted(grounded)
    return None


def _check_reply(callback_context, llm_response):
    """Final-text replies only: enforce 'numbers come from tools' and the 3-sentence cap."""
    content = llm_response.content
    if not content or not content.parts or any(p.function_call for p in content.parts):
        return None
    text = "".join(p.text or "" for p in content.parts if not p.thought).strip()
    if not text:
        return None
    state = callback_context.state
    user_text = ""
    if callback_context.user_content and callback_context.user_content.parts:
        user_text = " ".join(p.text or "" for p in callback_context.user_content.parts).strip()
    if user_text and not state.get("turn_tool_calls") and _PROMISE.search(text):
        log.warning("reply promised a search without calling a tool (%r); searching for it", text)
        state["promise_searches"] = int(state.get("promise_searches", 0)) + 1
        call = types.FunctionCall(name="search_products", args={"query": user_text})
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=call)]))
    bad = guards.ungrounded(text, set(state.get("grounded", [])), guards.numbers_in(user_text))
    if guards.leaks_internals(text):
        log.warning("reply recites internal instructions or tool names (%r); replaced", text)
        state["guard_violations"] = int(state.get("guard_violations", 0)) + 1
        text = guards.REFUSAL_REPLY
    elif bad:
        log.warning("ungrounded numbers %s in reply %r; replaced", sorted(bad), text)
        state["guard_violations"] = int(state.get("guard_violations", 0)) + 1
        text = guards.FALLBACK_REPLY
    text = guards.limit_sentences(text)
    llm_response.content = types.Content(role="model", parts=[types.Part(text=text)])
    state["turn_reply"] = text
    return llm_response


def log_request(callback_context):
    """Publish the finished turn (automatic `log_request`)."""
    state = callback_context.state
    shopper_text = ""
    if callback_context.user_content and callback_context.user_content.parts:
        shopper_text = " ".join(p.text or "" for p in callback_context.user_content.parts).strip()
    transcript = list(state.get("transcript", []))
    calls = list(state.get("turn_tool_calls", []))
    # A product search starts a new request ("mau minyak" ... "kalau santan ada?"), so each product the shopper
    # asks about becomes its own signal; follow-ups without a search ("boleh", "di rak mana?") stay with it.
    request, request_start = int(state.get("request", 0)), int(state.get("request_start", 0))
    if any(c.get("name") == "search_products" for c in calls):
        if state.get("request_searched"):
            request += 1
        request_start = len(transcript)
        state["request_searched"] = True
    state["request"], state["request_start"] = request, request_start
    transcript.append({"role": "shopper", "text": shopper_text})
    transcript.append({"role": "agent", "text": state.get("turn_reply", "")})
    turn = int(state.get("turn", 0)) + 1
    event = ConversationEvent(
        conversation_id=state.get("conversation_id", ""),
        turn=turn,
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        store_id=state.get("store_id", ""),
        sandbox_id=state.get("sandbox_id"),
        channel="chat",
        transcript=transcript,
        tool_calls=calls,
        request=request,
        request_start=request_start,
    )
    try:
        get_publisher().publish(event)
        state["last_logged_turn"] = turn
    except Exception:  # best effort: never break the chat because logging failed
        log.exception("log_request failed for conversation %s", event.conversation_id)
    state["transcript"] = transcript
    state["turn"] = turn
    state["last_turn"] = {"tool_calls": list(state.get("turn_tool_calls", []))}  # read by the API layer
    state["turn_tool_calls"] = []
    state["turn_reply"] = ""
    return None


def build_shopper_agent(model=None) -> Agent:
    return Agent(
        name="shopper_agent",
        model=model or settings.gemini_model,
        instruction=INSTRUCTION,
        tools=[search_products, check_stock, find_alternatives, nearest_branch_with_stock],
        generate_content_config=_REPLY_CONFIG,
        planner=thinking_planner(),
        before_tool_callback=_force_store,
        after_tool_callback=_record_tool_result,
        after_model_callback=_check_reply,
        after_agent_callback=log_request,
    )


shopper_agent = build_shopper_agent()
