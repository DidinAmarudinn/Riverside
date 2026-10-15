"""Demand Radar API (FastAPI). Routes follow docs/api-contract.md.

Shopper and manager chat are wired to the ADK agents; the other endpoints still return placeholder payloads.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agents.manager import manager_agent
from .agents.runtime import AgentRuntime
from .agents.shopper import shopper_agent
from .config import settings
from .data import get_repo

app = FastAPI(title="Demand Radar API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShopperChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    store_id: str = "S01"
    message: str = Field(min_length=1, max_length=1000)


class ManagerChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1000)
    store_id: str = "S01"
    sku: str | None = Field(default=None, max_length=64)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "backend": settings.backend, "model": settings.gemini_model}


_shopper_runtime: AgentRuntime | None = None


def shopper_runtime() -> AgentRuntime:
    global _shopper_runtime
    if _shopper_runtime is None:
        _shopper_runtime = AgentRuntime(shopper_agent, app_name="shopper")
    return _shopper_runtime


@app.post("/api/shopper/chat")
async def shopper_chat(body: ShopperChatIn) -> dict:
    store = get_repo().get_store(body.store_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown store_id {body.store_id!r}")
    result = await shopper_runtime().run_turn(
        body.session_id, body.message, {"store_id": store["id"], "store_name": store["name"]}
    )
    return {
        "session_id": result.session_id,
        "reply": result.reply,
        "signal": {"conversation_id": result.session_id, "turn": result.turn, "logged": result.logged},
        "tool_calls": result.tool_calls,
        "error": result.error,
    }


_manager_runtime: AgentRuntime | None = None


def manager_runtime() -> AgentRuntime:
    global _manager_runtime
    if _manager_runtime is None:
        _manager_runtime = AgentRuntime(manager_agent, app_name="manager")
    return _manager_runtime


@app.post("/api/manager/chat")
async def manager_chat(body: ManagerChatIn) -> dict:
    context = f"(context: store_id={body.store_id}" + (f"; SKU on screen: {body.sku}" if body.sku else "") + ")"
    result = await manager_runtime().run_turn(body.session_id, f"{body.message}\n\n{context}", {})
    last = result.state.get("last_turn", {})
    return {
        "session_id": result.session_id,
        "reply": result.reply,
        "citations": last.get("citations", []),
        "unverified_numbers": last.get("unverified_numbers", []),
        "tool_calls": last.get("tool_calls", []) or result.tool_calls,
        "error": result.error,
    }


@app.get("/api/skus")
def list_skus(store_id: str = "S01") -> dict:
    return {"store_id": store_id, "items": []}


@app.get("/api/skus/{sku}")
def sku_detail(sku: str, store_id: str = "S01") -> dict:
    return {"sku": sku, "store_id": store_id, "history": [], "forecast_pos_only": [], "forecast_radar": []}


@app.get("/api/gaps")
def gaps(store_id: str | None = None) -> dict:
    return {"store_id": store_id, "items": []}


@app.get("/api/signals/recent")
def recent_signals(limit: int = 20) -> dict:
    return {"items": []}


@app.get("/api/experiment")
def experiment() -> dict:
    return {"status": "not_run"}


@app.post("/api/demo/reset")
def demo_reset() -> dict:
    return {"status": "reset"}


@app.post("/internal/pubsub/push")
def pubsub_push(envelope: dict) -> dict:
    # Pub/Sub push endpoint -> signal extractor. Wired later.
    return {"status": "accepted"}
