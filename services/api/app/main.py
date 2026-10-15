"""Demand Radar API (FastAPI). Routes follow docs/api-contract.md §3.

Kiosk messages run the shopper agent and manager chat runs the manager agent; the other endpoints still return
placeholder payloads in the contract's shape.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import contract
from .agents.manager import manager_agent
from .agents.runtime import AgentRuntime
from .agents.shopper import shopper_agent
from .config import settings
from .data import get_repo

app = FastAPI(title="Demand Radar API", version="0.2.0")
app.add_middleware(  # local dev only; in production Hosting rewrites /api/** so no CORS is needed
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- uniform errors: {"error": {"code", "message"}} ----------

def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = exc.detail if isinstance(exc.detail, str) and exc.detail.isidentifier() else f"http_{exc.status_code}"
    return error(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error(422, "invalid_request", "; ".join(e.get("msg", "") for e in exc.errors()))


# ---------- sandbox: every kiosk/manager/demo call carries X-Sandbox-Id (UUID v4) ----------

def sandbox_id(x_sandbox_id: str | None = Header(default=None)) -> str:
    try:
        value = uuid.UUID(x_sandbox_id or "")
    except ValueError:
        raise HTTPException(400, "invalid_sandbox_id") from None
    if value.version != 4:
        raise HTTPException(400, "invalid_sandbox_id")
    return str(value)  # TODO: create sandboxes/{id} in Firestore on first use


# ---------- request bodies ----------

class KioskSessionIn(BaseModel):
    storeId: str


class KioskMessageIn(BaseModel):
    text: str
    imageBase64: str | None = None
    audioBase64: str | None = None


class ManagerChatIn(BaseModel):
    sessionId: str | None = None
    message: str


class NextMorningIn(BaseModel):
    storeId: str


# ---------- public ----------

@app.get("/api/healthz")
def healthz() -> dict:
    return {"ok": True, "backend": settings.backend, "model": settings.gemini_model}


@app.get("/api/stores")
def stores() -> dict:
    return {"items": []}


@app.get("/api/products")
def products(q: str = "") -> dict:
    return {"items": []}


# ---------- kiosk (shopper agent) ----------

_shopper_runtime: AgentRuntime | None = None
_kiosk_sessions: dict[str, dict] = {}  # sessionId -> {storeId, sandboxId}; chat history lives in the agent runtime


def shopper_runtime() -> AgentRuntime:
    global _shopper_runtime
    if _shopper_runtime is None:
        _shopper_runtime = AgentRuntime(shopper_agent, app_name="shopper")
    return _shopper_runtime


@app.post("/api/kiosk/sessions")
def kiosk_session(body: KioskSessionIn, sandbox: str = Depends(sandbox_id)) -> dict:
    if get_repo().get_store(body.storeId) is None:
        raise HTTPException(404, "store_not_found")
    session_id = str(uuid.uuid4())
    _kiosk_sessions[session_id] = {"storeId": body.storeId, "sandboxId": sandbox}
    return {"sessionId": session_id}


@app.post("/api/kiosk/sessions/{session_id}/messages")
async def kiosk_message(session_id: str, body: KioskMessageIn, sandbox: str = Depends(sandbox_id)) -> dict:
    session = _kiosk_sessions.get(session_id)
    if session is None or session["sandboxId"] != sandbox:  # another visitor's session looks like a missing one
        raise HTTPException(404, "session_not_found")
    if body.imageBase64 or body.audioBase64:
        raise HTTPException(400, "unsupported_input")  # image/audio lists are optional in the contract; not built yet
    if not body.text.strip() or len(body.text) > 1000:
        raise HTTPException(422, "invalid_request")
    store = get_repo().get_store(session["storeId"])
    result = await shopper_runtime().run_turn(
        session_id, body.text,
        {"store_id": store["id"], "store_name": store["name"], "sandbox_id": sandbox},
    )
    last = result.state.get("last_turn", {})
    return {"reply": result.reply, **contract.kiosk_payload(last.get("tool_calls", []))}


# ---------- manager ----------

@app.get("/api/manager/{store_id}/overview")
def manager_overview(store_id: str, sandbox: str = Depends(sandbox_id)) -> dict:
    # Shapes: docs/api-contract.md §3.1 (Metrics, Recommendation).
    return {"storeId": store_id, "kpis": {"lostRevenueToday": 0, "unmetToday": 0, "stockoutSkus": 0}, "topRisks": []}


@app.get("/api/manager/{store_id}/recommendations")
def manager_recommendations(store_id: str, risk: str | None = None, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"storeId": store_id, "items": []}


@app.get("/api/manager/{store_id}/sku/{sku}")
def manager_sku(store_id: str, sku: str, sandbox: str = Depends(sandbox_id)) -> dict:
    # Shape: docs/api-contract.md §3.1 SkuDetail. Series stay separate; the UI merges them by date.
    return {
        "storeId": store_id, "sku": sku,
        "product": {"name": sku, "brand": "", "category": "", "packSize": "", "priceIdr": 0, "aisle": ""},
        "riskType": "reorder",
        "kpis": {"onHand": 0, "lostRevenueIdr": 0, "lostRevenueUnits": 0, "unmetRequests": 0, "stockoutDays": 0},
        "sales": [], "forecastA": [], "forecastB": [], "unmetDaily": [],
        "evidence": {"total": 0, "items": []},
        "reason": {"recommendedQtyA": 0, "recommendedQtyB": 0, "reasonText": ""},
    }


_manager_runtime: AgentRuntime | None = None


def manager_runtime() -> AgentRuntime:
    global _manager_runtime
    if _manager_runtime is None:
        _manager_runtime = AgentRuntime(manager_agent, app_name="manager")
    return _manager_runtime


@app.post("/api/manager/{store_id}/chat")
async def manager_chat(store_id: str, body: ManagerChatIn, sandbox: str = Depends(sandbox_id)) -> dict:
    if not body.message.strip() or len(body.message) > 1000:
        raise HTTPException(422, "invalid_request")
    session_id = body.sessionId or str(uuid.uuid4())
    # the agent session is namespaced by sandbox so one visitor cannot continue another's conversation
    result = await manager_runtime().run_turn(
        f"{sandbox}:{session_id}", f"{body.message}\n\n(context: store_id={store_id})", {"sandbox_id": sandbox}
    )
    last = result.state.get("last_turn", {})
    return {
        "reply": contract.strip_markers(result.reply),
        "citations": contract.citations(last.get("citations", [])),
        "sessionId": session_id,
    }


@app.get("/api/manager/{store_id}/gaps")
def manager_gaps(store_id: str, sandbox: str = Depends(sandbox_id)) -> dict:
    # Shape: docs/api-contract.md §3.1 GapItem; the UI builds the per-category summary.
    return {"storeId": store_id, "items": []}


# ---------- demo ----------

@app.post("/api/demo/reset", status_code=204)
def demo_reset(sandbox: str = Depends(sandbox_id)) -> Response:
    # TODO: delete sandboxes/{sandbox} content; base data is never touched.
    return Response(status_code=204)


@app.post("/api/demo/next-morning")
def demo_next_morning(body: NextMorningIn, sandbox: str = Depends(sandbox_id)) -> dict:
    # TODO: recompute the hero scenario with the reorder formula (build plan §7) into the sandbox.
    return {"storeId": body.storeId, "updated": 0}


# ---------- Pub/Sub push (not behind Hosting; Pub/Sub calls the Cloud Run URL directly) ----------

def verify_pubsub_token(authorization: str | None) -> bool:
    """Accept only Google-signed OIDC tokens for our audience, minted for the push service account."""
    if not authorization or not authorization.startswith("Bearer ") or not settings.pubsub_audience:
        return False
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(authorization[7:], google_requests.Request(),
                                              audience=settings.pubsub_audience)
    except ValueError:
        return False
    return claims.get("email") == settings.pubsub_invoker_email and claims.get("email_verified", False)


@app.post("/pubsub/extract", status_code=204)
async def pubsub_extract(request: Request, authorization: str | None = Header(default=None)) -> Response:
    # Auth before reading the body, so unauthenticated calls always get 401.
    if not await run_in_threadpool(verify_pubsub_token, authorization):
        raise HTTPException(401, "invalid_token")
    envelope = await request.json()  # noqa: F841
    # TODO: decode envelope["message"]["data"], run Gemini extraction, write demand_signals + sandbox liveSignals.
    return Response(status_code=204)
