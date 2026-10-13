"""Structured-output schema for demand-signal extraction (Gemini response_schema)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    bought = "bought"
    out_of_stock = "out_of_stock"
    not_stocked = "not_stocked"
    substituted = "substituted"


class ExtractedItem(BaseModel):
    mentioned_text: str = Field(description="What the shopper said, verbatim")
    sku: str | None = Field(default=None, description="Matched SKU from the candidate list, else null")
    match_confidence: float = Field(ge=0, le=1)
    outcome: Outcome
    qty: int = 1
    substitute_sku: str | None = None
    requested_item: str | None = Field(default=None, description="Normalized name when the item is not sold")
    category_guess: str | None = None


class ExtractionResult(BaseModel):
    items: list[ExtractedItem] = Field(default_factory=list)
