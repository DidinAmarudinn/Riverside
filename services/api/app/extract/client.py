"""Gemini structured-output call for extraction (build plan §6.1).

Reuses the prompt and schema already in this package. Returns the first extracted item as a plain dict
(conversations carry one demand item); outcome is decided later by rules in core.extract_one.
"""
from __future__ import annotations

import json
import os
import random
import time

from .catalog import Catalog
from .core import parse_turns
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import ExtractionResult


def make_client(project: str | None, location: str | None):
    """Vertex AI client, or an API-key client when GEMINI_API_KEY is set."""
    from google import genai  # imported lazily so offline/template runs need no GCP deps

    if os.getenv("GEMINI_API_KEY"):
        return genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return genai.Client(vertexai=True, project=project, location=location or "global")


LIVE_TIMEOUT_MS = int(os.getenv("GEMINI_LIVE_TIMEOUT_MS", "6000"))  # measured 1.6-3.1 s per call


def live_client():
    """Cached Vertex client for the live /pubsub/extract path: one short-timeout call per kiosk turn."""
    global _live
    if _live is None:
        from google import genai
        from google.genai import types

        from ..config import settings

        _live = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gcp_location,
                             http_options=types.HttpOptions(timeout=LIVE_TIMEOUT_MS))
    return _live


_live = None


def _flatten(transcript) -> str:
    turns = parse_turns(transcript)
    return "\n".join(f"{'Shopper' if t.get('role') == 'shopper' else 'Agent'}: {t.get('text', '')}"
                     for t in turns)


def extract_item(client, model: str, transcript, catalog: Catalog, retries: int = 5,
                 thinking_budget: int | None = None) -> dict | None:
    """Call Gemini once for a conversation; return the first item dict, or None on repeated failure."""
    from google.genai import types

    cat_dicts = [{"sku": p.sku, "name": p.normalized_name, "synonyms": list(p.synonyms)} for p in catalog.carried]
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=ExtractionResult,
        temperature=0.0,
        # live path passes 0 (no thinking: lower latency); batch keeps the model default
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget) if thinking_budget is not None else None,
    )
    user = build_user_prompt(_flatten(transcript), cat_dicts)
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(model=model, contents=user, config=cfg)
            items = json.loads(resp.text).get("items", [])
            return items[0] if items else None
        except Exception as e:  # noqa: BLE001 - network/quota/parse; retry with backoff
            if attempt == retries - 1:
                print(f"  gemini failed after {retries} tries ({type(e).__name__}: {e})")
                return None
            time.sleep(min(60, 2 ** attempt + random.random()))
    return None
