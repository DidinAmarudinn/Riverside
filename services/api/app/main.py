"""Demand Radar API (FastAPI). Routes follow docs/api-contract.md §3.

Scaffold stage: endpoints return placeholder payloads in the contract's shape; real logic is wired in later.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import json
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings

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

@app.post("/api/kiosk/sessions")
def kiosk_session(body: KioskSessionIn, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"sessionId": str(uuid.uuid4())}


@app.post("/api/kiosk/sessions/{session_id}/messages")
def kiosk_message(session_id: str, body: KioskMessageIn, sandbox: str = Depends(sandbox_id)) -> dict:
    # TODO: shopper agent (ADK) + publish {sandboxId, storeId, transcript, tool results} to Pub/Sub.
    return {"reply": "(shopper agent not wired yet)", "products": [], "alternatives": [], "nearestBranch": None}


# ---------- manager ----------

@app.get("/api/manager/{store_id}/overview")
def manager_overview(store_id: str, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"storeId": store_id, "kpis": {}, "topRisks": []}


@app.get("/api/manager/{store_id}/recommendations")
def manager_recommendations(store_id: str, risk: str | None = None, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"storeId": store_id, "items": []}


@app.get("/api/manager/{store_id}/sku/{sku}")
def manager_sku(store_id: str, sku: str, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"storeId": store_id, "sku": sku, "sales": [], "forecastA": [], "forecastB": [], "unmetDaily": [],
            "evidence": [], "reason": None}


@app.post("/api/manager/{store_id}/chat")
def manager_chat(store_id: str, body: ManagerChatIn, sandbox: str = Depends(sandbox_id)) -> dict:
    # TODO: manager agent (ADK) with read-only BigQuery tools; answers cite numbers and sources.
    return {"reply": "(manager agent not wired yet)", "citations": [], "sessionId": body.sessionId or str(uuid.uuid4())}


@app.get("/api/manager/{store_id}/gaps")
def manager_gaps(store_id: str, sandbox: str = Depends(sandbox_id)) -> dict:
    return {"storeId": store_id, "categories": []}


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


EXTRACTOR_VERSION = "extractor-v1-" + dt.date.today().strftime("%Y%m%d")


def _conversation_from_message(data: dict) -> dict | None:
    """Map a published kiosk message to the conversation dict extract_one expects."""
    transcript = data.get("transcript")
    if transcript is None:
        return None
    return {
        "conversation_id": data.get("conversationId") or data.get("conversation_id") or str(uuid.uuid4()),
        "sandbox_id": data.get("sandboxId") or data.get("sandbox_id"),
        "store_id": data.get("storeId") or data.get("store_id"),
        "ts": data.get("ts") or dt.datetime.now(dt.timezone.utc).isoformat(),
        "transcript": transcript if isinstance(transcript, str) else json.dumps(transcript, ensure_ascii=False),
    }


def process_pubsub_message(data: dict) -> None:
    """Extract one conversation and, on the gcp backend, write the signal to BigQuery + Firestore."""
    from .extract.catalog import load_catalog
    from .extract.core import extract_one

    conv = _conversation_from_message(data)
    if conv is None:
        return
    row = extract_one(conv, load_catalog(), model_version=EXTRACTOR_VERSION)
    if settings.backend == "gcp":
        from .extract import sink
        sink.write_signal(row)


@app.post("/pubsub/extract", status_code=204)
async def pubsub_extract(request: Request, authorization: str | None = Header(default=None)) -> Response:
    # Auth before reading the body, so unauthenticated calls always get 401.
    if not await run_in_threadpool(verify_pubsub_token, authorization):
        raise HTTPException(401, "invalid_token")
    envelope = await request.json()
    message = (envelope or {}).get("message") or {}
    try:
        data = json.loads(base64.b64decode(message.get("data", "")).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return Response(status_code=204)  # ack malformed payloads so Pub/Sub stops redelivering
    await run_in_threadpool(process_pubsub_message, data)
    return Response(status_code=204)
