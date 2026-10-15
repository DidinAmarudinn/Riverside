"""Scripted stand-in for Gemini so agent loops (tool call -> guard -> publish) run offline."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr


def call(name: str, **args) -> tuple:
    return ("call", name, args)


def say(text: str) -> tuple:
    return ("say", text)


class ScriptedLlm(BaseLlm):
    """Plays `steps` in order, one per model call. A turn ends at the first `say`.

    Steps of the next turn are consumed on the following run, so scripts can span several user turns.
    """

    model: str = "scripted"
    _steps: list = PrivateAttr(default_factory=list)
    seen_requests: list = []

    def __init__(self, steps: list):
        super().__init__()
        self._steps = list(steps)
        self.seen_requests = []

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False
                                     ) -> AsyncGenerator[LlmResponse, None]:
        self.seen_requests.append(llm_request)
        if not self._steps:
            raise AssertionError("ScriptedLlm ran out of steps")
        step = self._steps.pop(0)
        if step[0] == "call":
            part = types.Part(function_call=types.FunctionCall(name=step[1], args=step[2]))
        else:
            part = types.Part(text=step[1])
        yield LlmResponse(content=types.Content(role="model", parts=[part]))
