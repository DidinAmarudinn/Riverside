#!/usr/bin/env python3
"""End-to-end smoke test against a deployed Demand Radar (Gate 1+, judge checklist).

Checks the public chain from the outside, the same way a judge would:
  hosting pages -> /api/healthz -> kiosk message -> Pub/Sub -> extractor -> Firestore liveSignals,
plus the security checks (/pubsub/extract without token = 401, sessions not publicly readable).

Standard library only. Usage:
  BASE_URL=https://<project>.web.app RUN_URL=https://demand-radar-api-xxxx.run.app \
  FIREBASE_PROJECT=<project-id> python3 infra/smoke_test.py

Optional env: STORE_ID (default S01), KIOSK_TEXT, SIGNAL_TIMEOUT (seconds, default 15).
Paths follow the build plan contract (§4.3); override with HEALTH_PATH, KIOSK_SESSIONS_PATH,
EXTRACT_PATH if the API differs.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
RUN_URL = os.getenv("RUN_URL", "").rstrip("/")
FIREBASE_PROJECT = os.getenv("FIREBASE_PROJECT", "")
STORE_ID = os.getenv("STORE_ID", "S01")
KIOSK_TEXT = os.getenv("KIOSK_TEXT", "ada santan kotak kecil?")
SIGNAL_TIMEOUT = float(os.getenv("SIGNAL_TIMEOUT", "15"))
HEALTH_PATH = os.getenv("HEALTH_PATH", "/api/healthz")
KIOSK_SESSIONS_PATH = os.getenv("KIOSK_SESSIONS_PATH", "/api/kiosk/sessions")
EXTRACT_PATH = os.getenv("EXTRACT_PATH", "/pubsub/extract")

SANDBOX_ID = str(uuid.uuid4())
results: list[tuple[str, str, str]] = []  # (status, check, detail)


def record(ok: bool | None, check: str, detail: str = "") -> bool:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((status, check, detail))
    print(f"[{status}] {check}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


def http(method: str, url: str, body: dict | None = None, timeout: float = 20) -> tuple[int, str, float]:
    """Return (status, text, seconds). Status 0 means the request never got a response."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Sandbox-Id", SANDBOX_ID)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read().decode(errors="replace"), time.monotonic() - start
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), time.monotonic() - start
    except Exception as e:  # DNS, TLS, timeout
        return 0, f"{type(e).__name__}: {e}", time.monotonic() - start


def as_json(text: str) -> dict | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


def firestore_list(path: str) -> tuple[int, list]:
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{path}"
    status, text, _ = http("GET", url, timeout=10)
    docs = (as_json(text) or {}).get("documents", []) if status == 200 else []
    return status, docs


def check_hosting() -> None:
    for page in ("/", "/kiosk", "/manager"):
        status, text, secs = http("GET", BASE_URL + page)
        record(status == 200 and "<html" in text.lower(), f"Hosting {page} opens", f"HTTP {status}, {secs:.1f}s")


def check_health() -> bool:
    status, text, secs = http("GET", BASE_URL + HEALTH_PATH)
    return record(status == 200 and as_json(text) is not None,
                  f"{HEALTH_PATH} via Hosting rewrite", f"HTTP {status}, {secs:.1f}s, body {text[:80]!r}")


def check_extract_requires_token() -> None:
    if not RUN_URL:
        record(None, f"{EXTRACT_PATH} rejects calls without OIDC token", "RUN_URL not set")
        return
    fake = {"message": {"data": "e30=", "messageId": "smoke"}, "subscription": "smoke"}
    status, _, _ = http("POST", RUN_URL + EXTRACT_PATH, fake)
    record(status == 401, f"{EXTRACT_PATH} rejects calls without OIDC token", f"HTTP {status} (want 401)")


def check_kiosk_to_signal() -> None:
    status, text, secs = http("POST", BASE_URL + KIOSK_SESSIONS_PATH, {"storeId": STORE_ID})
    session_id = (as_json(text) or {}).get("sessionId")
    if not record(status == 200 and bool(session_id), "Create kiosk session", f"HTTP {status}, {secs:.1f}s"):
        record(None, "Kiosk reply / live signal", "no session, skipped")
        return

    sent_at = time.monotonic()
    status, text, secs = http("POST", f"{BASE_URL}{KIOSK_SESSIONS_PATH}/{session_id}/messages", {"text": KIOSK_TEXT}, timeout=30)
    reply = (as_json(text) or {}).get("reply", "")
    record(status == 200 and bool(reply) and secs < 10, "Kiosk agent replies in < 10 s",
           f"HTTP {status}, {secs:.1f}s, reply {reply[:80]!r}")
    if status != 200:
        return

    if not FIREBASE_PROJECT:
        record(None, "Live signal appears in Firestore", "FIREBASE_PROJECT not set")
        return
    path = f"sandboxes/{SANDBOX_ID}/liveSignals"
    while True:
        fs_status, docs = firestore_list(path)
        waited = time.monotonic() - sent_at
        if docs or waited > SIGNAL_TIMEOUT:
            break
        time.sleep(1)
    if docs:
        record(waited <= 5, "Live signal appears in Firestore in < 5 s", f"{len(docs)} doc(s) after {waited:.1f}s")
    else:
        record(False, "Live signal appears in Firestore in < 5 s",
               f"none after {waited:.0f}s (last HTTP {fs_status}) at {path}")


def check_sessions_private() -> None:
    if not FIREBASE_PROJECT:
        record(None, "Firestore sessions are not publicly readable", "FIREBASE_PROJECT not set")
        return
    status, _ = firestore_list(f"sandboxes/{SANDBOX_ID}/sessions")
    record(status in (401, 403), "Firestore sessions are not publicly readable", f"HTTP {status} (want 403)")


def main() -> int:
    if not BASE_URL:
        print(__doc__)
        return 2
    print(f"Target {BASE_URL}  sandbox {SANDBOX_ID}\n")
    check_hosting()
    if check_health():
        check_kiosk_to_signal()
    else:
        record(None, "Kiosk reply / live signal", "API unreachable, skipped")
    check_extract_requires_token()
    check_sessions_private()

    failed = [r for r in results if r[0] == "FAIL"]
    skipped = [r for r in results if r[0] == "SKIP"]
    passed = len(results) - len(failed) - len(skipped)
    print(f"\n{passed} passed, {len(failed)} failed, {len(skipped)} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
