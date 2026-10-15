"""Gemini request settings shared by the agents."""
from __future__ import annotations

from google.adk.planners import BuiltInPlanner
from google.genai import types

from ..config import settings


def thinking_planner() -> BuiltInPlanner | None:
    """Planner that pins Gemini's thinking budget (ADK rejects thinking_config in generate_content_config).

    None when GEMINI_THINKING_BUDGET is negative, i.e. keep the model's default dynamic thinking."""
    budget = settings.gemini_thinking_budget
    if budget < 0:
        return None
    return BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=budget))


def reply_config(temperature: float = 0.3) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=temperature,
        http_options=types.HttpOptions(
            timeout=20_000,  # docs/limits.md: demo-critical calls time out at 20 s
            retry_options=types.HttpRetryOptions(
                attempts=3, initial_delay=1.0, max_delay=8.0, exp_base=2.0, jitter=0.5,
                http_status_codes=[429, 503, 504],
            ),
        ),
    )
