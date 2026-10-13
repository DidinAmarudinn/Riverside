"""Demand Radar API (FastAPI). Routes follow docs/api-contract.md.

Scaffold stage: endpoints return placeholder payloads; real logic is wired in later.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings

app = FastAPI(title="Demand Radar API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShopperChatIn(BaseModel):
    session_id: str
    store_id: str = "S01"
    message: str


class ManagerChatIn(BaseModel):
    session_id: str
    message: str
    store_id: str = "S01"
    sku: str | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "backend": settings.backend, "model": settings.gemini_model}


@app.post("/api/shopper/chat")
def shopper_chat(body: ShopperChatIn) -> dict:
    # TODO: app.agents.shopper (ADK) + publish conversation for signal extraction.
    return {"session_id": body.session_id, "reply": "(shopper agent not wired yet)", "signal": None}


@app.post("/api/manager/chat")
def manager_chat(body: ManagerChatIn) -> dict:
    # TODO: app.agents.manager (ADK) with BigQuery tools.
    return {"session_id": body.session_id, "reply": "(manager agent not wired yet)", "tool_calls": []}


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
