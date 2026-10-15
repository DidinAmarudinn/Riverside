"""Run ADK agents one chat turn at a time and hand back a plain result for the API layer."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

log = logging.getLogger(__name__)

USER_ID = "kiosk"  # one anonymous shopper per session; the session id identifies the conversation
ERROR_REPLY = "Maaf kak, sistemnya lagi agak ramai. Coba kirim lagi sebentar ya."


@dataclass
class TurnResult:
    reply: str
    session_id: str
    turn: int = 0
    logged: bool = False
    tool_calls: list[dict] = field(default_factory=list)
    state: dict = field(default_factory=dict)  # session state after the turn (agent-specific keys)
    error: str | None = None


class AgentRuntime:
    def __init__(self, agent: BaseAgent, app_name: str):
        self.app_name = app_name
        self.sessions = InMemorySessionService()
        self.runner = Runner(agent=agent, app_name=app_name, session_service=self.sessions)
        self._locks: dict[str, asyncio.Lock] = {}

    async def _ensure_session(self, session_id: str, state: dict):
        session = await self.sessions.get_session(app_name=self.app_name, user_id=USER_ID, session_id=session_id)
        if session is None:
            session = await self.sessions.create_session(
                app_name=self.app_name, user_id=USER_ID, session_id=session_id, state=state
            )
        return session

    async def run_turn(self, session_id: str, message: str, initial_state: dict) -> TurnResult:
        # one turn at a time per conversation, so state updates from overlapping requests do not interleave
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            await self._ensure_session(session_id, {**initial_state, "conversation_id": session_id})
            content = types.Content(role="user", parts=[types.Part(text=message)])
            reply = ""
            try:
                async for event in self.runner.run_async(
                    user_id=USER_ID, session_id=session_id, new_message=content
                ):
                    if event.is_final_response() and event.content and event.content.parts:
                        reply = "".join(p.text or "" for p in event.content.parts if not p.thought).strip()
            except Exception as exc:  # Gemini 429/timeout after retries, etc.: degrade, do not 500
                log.exception("agent turn failed for session %s", session_id)
                return TurnResult(reply=ERROR_REPLY, session_id=session_id, error=type(exc).__name__)
            session = await self.sessions.get_session(
                app_name=self.app_name, user_id=USER_ID, session_id=session_id
            )
            state = session.state if session else {}
            turn = int(state.get("turn", 0))
            return TurnResult(
                reply=reply or ERROR_REPLY,
                session_id=session_id,
                turn=turn,
                logged=state.get("last_logged_turn") == turn and turn > 0,
                tool_calls=self._tool_calls_of(session),
                state=dict(state),
            )

    @staticmethod
    def _tool_calls_of(session) -> list[dict]:
        """Tool calls of the latest turn, read from the event log (state is reset at turn end)."""
        if session is None:
            return []
        calls: list[dict] = []
        for ev in session.events:
            if ev.author == "user":
                calls = []  # a new user message starts a new turn
                continue
            for part in (ev.content.parts if ev.content and ev.content.parts else []):
                if part.function_call:
                    calls.append({"name": part.function_call.name, "args": dict(part.function_call.args or {})})
        return calls
