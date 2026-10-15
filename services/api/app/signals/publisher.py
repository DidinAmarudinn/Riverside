"""Publish one event per shopper-agent turn so the signal extractor can turn it into demand signals.

The shopper agent calls `log_request` automatically at the end of every turn (see agents/shopper.py), so a
request is captured even if the model forgets. Publishing is best-effort: it must never break the chat.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Protocol

from ..config import settings

log = logging.getLogger(__name__)


@dataclass
class ConversationEvent:
    """One completed agent turn. `transcript` is the whole conversation so far; the extractor keeps the
    latest turn per `conversation_id`. `tool_calls` carry the grounded stock/search results, so an
    out-of-stock outcome does not have to be guessed from chat text."""

    conversation_id: str
    turn: int
    ts: str
    store_id: str
    channel: str
    transcript: list[dict]
    tool_calls: list[dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class Publisher(Protocol):
    def publish(self, event: ConversationEvent) -> None: ...


class LocalPublisher:
    """Keeps the latest events in memory (dev/tests). The extractor reads them via `drain()`/`recent()`."""

    def __init__(self, maxlen: int = 1000):
        self._events: deque[ConversationEvent] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def publish(self, event: ConversationEvent) -> None:
        with self._lock:
            self._events.append(event)

    def recent(self, limit: int = 20) -> list[ConversationEvent]:
        with self._lock:
            return list(self._events)[-limit:][::-1]

    def drain(self) -> list[ConversationEvent]:
        with self._lock:
            out = list(self._events)
            self._events.clear()
            return out


class PubSubPublisher:
    def __init__(self, project: str, topic: str):
        from google.cloud import pubsub_v1

        self._client = pubsub_v1.PublisherClient()
        self._path = self._client.topic_path(project, topic)

    def publish(self, event: ConversationEvent) -> None:
        future = self._client.publish(
            self._path,
            event.to_json().encode("utf-8"),
            conversation_id=event.conversation_id, store_id=event.store_id, turn=str(event.turn),
        )
        future.add_done_callback(_log_failure)


def _log_failure(future) -> None:
    exc = future.exception()
    if exc:
        log.error("pubsub publish failed: %s", exc)


@lru_cache(maxsize=1)
def get_publisher() -> Publisher:
    if settings.publisher == "pubsub":
        return PubSubPublisher(settings.gcp_project, settings.pubsub_topic)
    return LocalPublisher()


def reset_publisher_cache() -> None:
    get_publisher.cache_clear()
