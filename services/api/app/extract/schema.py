"""Structured-output schema for demand-signal extraction (build plan §6, contract docs/api-contract.md §1).

Gemini returns what the shopper asked for; it never decides the outcome. The outcome comes from rules over the
stock state at that moment (tool-call results on the live path, stock_events on the batch path).
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

CONFIDENCE_THRESHOLD = 0.7  # below this a signal is stored as low_confidence and left out of forecast B


class Intent(str, Enum):
    ask_location = "ask_location"
    ask_availability = "ask_availability"
    buy = "buy"
    complain = "complain"


class Outcome(str, Enum):
    """demand_signals.outcome, decided by rules (not by the model)."""
    purchased = "purchased"
    out_of_stock = "out_of_stock"
    not_carried = "not_carried"
    substituted = "substituted"
    low_confidence = "low_confidence"


class ExtractedItem(BaseModel):
    requested_text: str = Field(description="What the shopper asked for, verbatim")
    sku: str | None = Field(default=None, description="Matched SKU from the catalog, or null if not in the catalog")
    normalized_name: str = Field(description="Clean product name, also for items the store does not carry")
    category: str
    intent: Intent
    accepted_substitute: str | None = Field(default=None, description="SKU of an alternative the shopper accepted")
    qty: int = 1
    confidence: float = Field(ge=0, le=1)


class ExtractionResult(BaseModel):
    items: list[ExtractedItem] = Field(default_factory=list)


def decide_outcome(item: ExtractedItem, stock_on_hand: int | None) -> Outcome:
    """Rules from build plan §6.3."""
    if item.confidence < CONFIDENCE_THRESHOLD:
        return Outcome.low_confidence
    if item.sku is None:
        return Outcome.not_carried
    if item.accepted_substitute:
        return Outcome.substituted
    if stock_on_hand == 0:
        return Outcome.out_of_stock
    return Outcome.purchased
