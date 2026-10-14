#!/usr/bin/env python3
"""End-to-end smoke test against a deployed Demand Radar: Gate 1 chain + judge checklist (build plan §15).

Checks the public app from the outside, the same way a judge would, each run in fresh sandboxes:
  gate1  hosting pages -> /api/healthz -> kiosk message -> Pub/Sub -> extractor -> Firestore liveSignals,
         /pubsub/extract without token = 401, sessions not publicly readable.
  judge  everything in gate1 plus: page load < 3 s, informal/typo input, out-of-stock rescue, demo reset,
         two concurrent sandboxes isolated, hero scenario A ~ 0 / B ~ 60, evidence, manager agent answers
         with numbers, assortment gaps, /about names the Google services, forbidden terms absent.
Checks that need human eyes are printed as a manual list at the end.

Standard library only. Usage:
  BASE_URL=https://<project>.web.app RUN_URL=https://demand-radar-api-xxxx.run.app \
  FIREBASE_PROJECT=<project-id> python3 infra/smoke_test.py [gate1|judge]     (default: judge)

Optional env:
  STORE_ID (S01), HERO_QUERY ("santan kotak 65"), HERO_SKU (skip the product lookup),
  HERO_A_MAX (5), HERO_B_RANGE ("50-70"), SIGNAL_TIMEOUT (15 s), AGENT_TIMEOUT (30 s),
  FORBIDDEN_TERMS: comma-separated words that must not appear in the UI bundle or any API response.
    Keep the values in your local shell, never in the repo.
Paths follow the build plan contract (§4.3); override with HEALTH_PATH, KIOSK_SESSIONS_PATH, EXTRACT_PATH,
MANAGER_PATH, PRODUCTS_PATH, DEMO_PATH if the API differs.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
RUN_URL = os.getenv("RUN_URL", "").rstrip("/")
FIREBASE_PROJECT = os.getenv("FIREBASE_PROJECT", "")
FIRESTORE_BASE = os.getenv("FIRESTORE_BASE", "https://firestore.googleapis.com").rstrip("/")
STORE_ID = os.getenv("STORE_ID", "S01")
HERO_QUERY = os.getenv("HERO_QUERY", "santan kotak 65")
HERO_SKU = os.getenv("HERO_SKU", "")
HERO_A_MAX = float(os.getenv("HERO_A_MAX", "5"))
HERO_B_MIN, HERO_B_MAX = (float(v) for v in os.getenv("HERO_B_RANGE", "50-70").split("-"))
SIGNAL_TIMEOUT = float(os.getenv("SIGNAL_TIMEOUT", "15"))
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "30"))
FORBIDDEN_TERMS = [t.strip().lower() for t in os.getenv("FORBIDDEN_TERMS", "").split(",") if t.strip()]
HEALTH_PATH = os.getenv("HEALTH_PATH", "/api/healthz")
KIOSK_SESSIONS_PATH = os.getenv("KIOSK_SESSIONS_PATH", "/api/kiosk/sessions")
EXTRACT_PATH = os.getenv("EXTRACT_PATH", "/pubsub/extract")
MANAGER_PATH = os.getenv("MANAGER_PATH", "/api/manager")
PRODUCTS_PATH = os.getenv("PRODUCTS_PATH", "/api/products")
DEMO_PATH = os.getenv("DEMO_PATH", "/api/demo")

KIOSK_TEXT = "ada santan kotak kecil?"
KIOSK_TYPO_TEXT = "kak ad santen kotak yg kcil gk?"
MANAGER_QUESTIONS = [
    "Why should I order 60 boxes of coconut milk?",
    "Which products are most at risk of stocking out this week?",
    "What are shoppers asking for that we don't sell?",
    "How much revenue did we lose to stockouts yesterday?",
]
ABOUT_TERMS = ["Firebase", "Firestore", "Cloud Run", "Gemini"]
MANUAL_CHECKS = [
    "Open / in an incognito window: the page explains in a few sentences what to try.",
    "Evidence drawer on the hero SKU shows each quote with a 'Simulated conversation' label.",
    "Run the hero scenario in two incognito windows at once and watch each dashboard update only for itself.",
    "Manager answers read well and cite the right numbers (the script only checks that numbers are present).",
    "Layout at 1366 px wide: no cut-off text, loading and error states look friendly.",
]

results: list[tuple[str, str, str]] = []  # (status, check, detail)
seen_bodies: list[str] = []  # every response body, scanned for forbidden terms at the end


def record(ok: bool | None, check: str, detail: str = "") -> bool:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((status, check, detail))
    print(f"[{status}] {check}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


def http(method: str, url: str, body: dict | None = None, sandbox: str | None = None,
         timeout: float = 20) -> tuple[int, str, float]:
    """Return (status, text, seconds). Status 0 means the request never got a response."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if sandbox:
        req.add_header("X-Sandbox-Id", sandbox)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            text = res.read().decode(errors="replace")
            status = res.status
    except urllib.error.HTTPError as e:
        text, status = e.read().decode(errors="replace"), e.code
    except Exception as e:  # DNS, TLS, timeout
        return 0, f"{type(e).__name__}: {e}", time.monotonic() - start
    seen_bodies.append(text)
    return status, text, time.monotonic() - start


def as_json(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return None


def walk(value):
    """Yield every dict nested anywhere inside a JSON value."""
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def first_list(value) -> list:
    """The first non-empty list inside a JSON value (tolerant of {items: [...]}, {gaps: [...]}, [...])."""
    if isinstance(value, list):
        return value
    for d in walk(value):
        for v in d.values():
            if isinstance(v, list) and v:
                return v
    return []


def firestore_list(path: str) -> tuple[int, list]:
    url = f"{FIRESTORE_BASE}/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{path}"
    status, text, _ = http("GET", url, timeout=10)
    docs = (as_json(text) or {}).get("documents", []) if status == 200 else []
    return status, docs


def wait_for_signals(sandbox: str, since: float) -> tuple[list, float, int]:
    while True:
        status, docs = firestore_list(f"sandboxes/{sandbox}/liveSignals")
        waited = time.monotonic() - since
        if docs or waited > SIGNAL_TIMEOUT:
            return docs, waited, status
        time.sleep(1)


class Kiosk:
    def __init__(self, sandbox: str):
        self.sandbox = sandbox
        self.session_id = None

    def open(self) -> tuple[bool, str]:
        status, text, secs = http("POST", BASE_URL + KIOSK_SESSIONS_PATH, {"storeId": STORE_ID}, self.sandbox)
        self.session_id = (as_json(text) or {}).get("sessionId")
        return status == 200 and bool(self.session_id), f"HTTP {status}, {secs:.1f}s"

    def say(self, message: str) -> tuple[int, dict, float]:
        url = f"{BASE_URL}{KIOSK_SESSIONS_PATH}/{self.session_id}/messages"
        status, text, secs = http("POST", url, {"text": message}, self.sandbox, timeout=AGENT_TIMEOUT)
        return status, as_json(text) or {}, secs


# ---------------------------------------------------------------- gate 1

def check_hosting(judge: bool) -> None:
    for page in ("/", "/kiosk", "/manager"):
        status, text, secs = http("GET", BASE_URL + page)
        ok = status == 200 and "<html" in text.lower() and (not judge or page != "/" or secs < 3)
        record(ok, f"Hosting {page} opens" + (" in < 3 s" if judge and page == "/" else ""), f"HTTP {status}, {secs:.1f}s")


def check_health() -> bool:
    status, text, secs = http("GET", BASE_URL + HEALTH_PATH)
    return record(status == 200 and isinstance(as_json(text), dict),
                  f"{HEALTH_PATH} via Hosting rewrite", f"HTTP {status}, {secs:.1f}s, body {text[:60]!r}")


def check_kiosk_to_signal(sandbox: str) -> None:
    kiosk = Kiosk(sandbox)
    ok, detail = kiosk.open()
    if not record(ok, "Create kiosk session", detail):
        return
    sent_at = time.monotonic()
    status, body, secs = kiosk.say(KIOSK_TEXT)
    reply = body.get("reply", "")
    record(status == 200 and bool(reply) and secs < 10, "Kiosk agent replies in < 10 s",
           f"HTTP {status}, {secs:.1f}s, reply {reply[:70]!r}")
    if status != 200:
        return
    if not FIREBASE_PROJECT:
        record(None, "Live signal appears in Firestore in < 5 s", "FIREBASE_PROJECT not set")
        return
    docs, waited, fs_status = wait_for_signals(sandbox, sent_at)
    detail = f"{len(docs)} doc(s) after {waited:.1f}s" if docs else f"none after {waited:.0f}s (HTTP {fs_status})"
    record(bool(docs) and waited <= 5, "Live signal appears in Firestore in < 5 s", detail)


def check_extract_requires_token() -> None:
    if not RUN_URL:
        record(None, f"{EXTRACT_PATH} rejects calls without OIDC token", "RUN_URL not set")
        return
    fake = {"message": {"data": "e30=", "messageId": "smoke"}, "subscription": "smoke"}
    status, _, _ = http("POST", RUN_URL + EXTRACT_PATH, fake)
    record(status == 401, f"{EXTRACT_PATH} rejects calls without OIDC token", f"HTTP {status} (want 401)")


def check_sessions_private(sandbox: str) -> None:
    if not FIREBASE_PROJECT:
        record(None, "Firestore sessions are not publicly readable", "FIREBASE_PROJECT not set")
        return
    status, _ = firestore_list(f"sandboxes/{sandbox}/sessions")
    record(status in (401, 403), "Firestore sessions are not publicly readable", f"HTTP {status} (want 403)")


# ---------------------------------------------------------------- judge checklist

def reset(sandbox: str) -> int:
    status, _, _ = http("POST", f"{BASE_URL}{DEMO_PATH}/reset", {}, sandbox)
    return status


def check_kiosk_language_and_rescue(sandbox: str) -> None:
    kiosk = Kiosk(sandbox)
    if not kiosk.open()[0]:
        record(False, "Kiosk understands informal text with typos", "could not open a session")
        return
    status, body, secs = kiosk.say(KIOSK_TYPO_TEXT)
    names = " ".join(str(p.get("name", "")) for p in body.get("products", []) if isinstance(p, dict)).lower()
    understood = "santan" in names or "santan" in str(body.get("reply", "")).lower()
    record(status == 200 and understood, "Kiosk understands informal text with typos",
           f"{KIOSK_TYPO_TEXT!r} -> products {names[:60]!r}, {secs:.1f}s")
    rescue = bool(body.get("alternatives")) or bool(body.get("nearestBranch"))
    record(status == 200 and rescue, "Out-of-stock item gets an alternative or nearest branch",
           f"alternatives={len(body.get('alternatives') or [])}, nearestBranch={bool(body.get('nearestBranch'))}")


def check_reset_and_isolation() -> None:
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    if not FIREBASE_PROJECT:
        record(None, "Demo reset clears the sandbox", "FIREBASE_PROJECT not set")
        record(None, "Two concurrent sandboxes stay isolated", "FIREBASE_PROJECT not set")
        return
    kiosk = Kiosk(a)
    if not kiosk.open()[0]:
        record(False, "Two concurrent sandboxes stay isolated", "could not open a session")
        return
    sent_at = time.monotonic()
    kiosk.say(KIOSK_TEXT)
    docs_a, _, _ = wait_for_signals(a, sent_at)
    _, docs_b = firestore_list(f"sandboxes/{b}/liveSignals")
    record(bool(docs_a) and not docs_b, "Two concurrent sandboxes stay isolated",
           f"sandbox A {len(docs_a)} signal(s), sandbox B {len(docs_b)}")
    status = reset(a)
    time.sleep(2)
    _, after = firestore_list(f"sandboxes/{a}/liveSignals")
    record(status in (200, 204) and not after, "Demo reset clears the sandbox",
           f"reset HTTP {status}, {len(after)} signal(s) left")


def resolve_hero_sku() -> str:
    if HERO_SKU:
        return HERO_SKU
    status, text, _ = http("GET", f"{BASE_URL}{PRODUCTS_PATH}?q={urllib.parse.quote(HERO_QUERY)}")
    items = first_list(as_json(text)) if status == 200 else []
    return str(items[0].get("sku", "")) if items and isinstance(items[0], dict) else ""


def pick_number(d: dict, patterns: list[str]) -> float | None:
    for key, value in d.items():
        if isinstance(value, (int, float)) and any(re.search(p, key, re.I) for p in patterns):
            return float(value)
    return None


def check_hero_scenario(sandbox: str, sku: str) -> None:
    if not sku:
        record(False, "Hero scenario: A ~ 0, B ~ 60", f"no SKU found for {HERO_QUERY!r} (set HERO_SKU)")
        return
    reset(sandbox)
    status, _, secs = http("POST", f"{BASE_URL}{DEMO_PATH}/next-morning", {"storeId": STORE_ID}, sandbox,
                           timeout=AGENT_TIMEOUT)
    if not record(status in (200, 204), "Next morning recomputes recommendations", f"HTTP {status}, {secs:.1f}s"):
        return
    status, text, _ = http("GET", f"{BASE_URL}{MANAGER_PATH}/{STORE_ID}/recommendations", sandbox=sandbox)
    rows = [d for d in walk(as_json(text)) if str(d.get("sku", "")) == sku]
    a = b = None
    for row in rows:
        a = pick_number(row, [r"recommended.*_?a$", r"^qty_?a$", r"order_?a"]) if a is None else a
        b = pick_number(row, [r"recommended.*_?b$", r"^qty_?b$", r"order_?b"]) if b is None else b
    ok = a is not None and b is not None and a <= HERO_A_MAX and HERO_B_MIN <= b <= HERO_B_MAX
    record(ok, f"Hero scenario: A <= {HERO_A_MAX:g}, B in {HERO_B_MIN:g}-{HERO_B_MAX:g}", f"sku {sku}: A={a}, B={b}")


def check_sku_evidence(sandbox: str, sku: str) -> None:
    if not sku:
        record(None, "SKU detail has conversation evidence", "no hero SKU")
        return
    status, text, secs = http("GET", f"{BASE_URL}{MANAGER_PATH}/{STORE_ID}/sku/{sku}", sandbox=sandbox)
    body = as_json(text) or {}
    evidence = body.get("evidence") if isinstance(body, dict) else None
    record(status == 200 and bool(evidence), "SKU detail has conversation evidence",
           f"HTTP {status}, {len(evidence or [])} quote(s), {secs:.1f}s")


def check_manager_agent(sandbox: str) -> None:
    session = None
    for q in MANAGER_QUESTIONS:
        status, text, secs = http("POST", f"{BASE_URL}{MANAGER_PATH}/{STORE_ID}/chat",
                                  {"sessionId": session, "message": q}, sandbox, timeout=AGENT_TIMEOUT)
        body = as_json(text) or {}
        session = body.get("sessionId", session)
        reply = str(body.get("reply", ""))
        record(status == 200 and bool(re.search(r"\d", reply)), f"Manager agent answers with numbers: {q!r}",
               f"HTTP {status}, {secs:.1f}s, {len(body.get('citations') or [])} citation(s)")


def check_gaps(sandbox: str) -> None:
    status, text, _ = http("GET", f"{BASE_URL}{MANAGER_PATH}/{STORE_ID}/gaps", sandbox=sandbox)
    items = first_list(as_json(text)) if status == 200 else []
    record(bool(items), "Assortment gaps page has data", f"HTTP {status}, {len(items)} item(s)")


def app_bundle_text() -> str:
    """index.html plus every JS file it loads: the SPA's routes (/about included) live in the bundle."""
    status, html, _ = http("GET", BASE_URL + "/")
    if status != 200:
        return ""
    parts = [html]
    for src in re.findall(r'<script[^>]+src="([^"]+)"', html):
        _, js, _ = http("GET", urllib.parse.urljoin(BASE_URL + "/", src))
        parts.append(js)
    return "\n".join(parts)


def check_about(bundle: str) -> None:
    missing = [t for t in ABOUT_TERMS if t.lower() not in bundle.lower()]
    record(bool(bundle) and not missing, "/about names Firebase, Firestore, Cloud Run, Gemini",
           "missing: " + ", ".join(missing) if missing else "all four found in the app bundle")


def check_forbidden_terms() -> None:
    if not FORBIDDEN_TERMS:
        record(None, "No forbidden terms in UI bundle or API responses", "FORBIDDEN_TERMS not set")
        return
    corpus = "\n".join(seen_bodies).lower()
    hits = [t for t in FORBIDDEN_TERMS if t in corpus]
    record(not hits, "No forbidden terms in UI bundle or API responses",
           f"{len(hits)} term(s) found" if hits else f"{len(seen_bodies)} responses scanned")


# ---------------------------------------------------------------- main

def main() -> int:
    suite = (sys.argv[1] if len(sys.argv) > 1 else "judge").lower()
    if not BASE_URL or suite not in ("gate1", "judge"):
        print(__doc__)
        return 2
    judge = suite == "judge"
    sandbox = str(uuid.uuid4())
    print(f"Suite {suite}  target {BASE_URL}  sandbox {sandbox}\n")

    check_hosting(judge)
    api_up = check_health()
    if api_up:
        check_kiosk_to_signal(sandbox)
    check_extract_requires_token()
    check_sessions_private(sandbox)

    if judge:
        if api_up:
            check_kiosk_language_and_rescue(str(uuid.uuid4()))
            check_reset_and_isolation()
            hero_box, sku = str(uuid.uuid4()), resolve_hero_sku()
            check_hero_scenario(hero_box, sku)
            check_sku_evidence(hero_box, sku)
            check_manager_agent(hero_box)
            check_gaps(hero_box)
        else:
            record(None, "API checks (kiosk, reset, hero, agent, gaps)", "API unreachable, skipped")
        check_about(app_bundle_text())
        check_forbidden_terms()
        print("\nManual checks (human eyes):")
        for item in MANUAL_CHECKS:
            print(f"  [ ] {item}")

    failed = sum(1 for r in results if r[0] == "FAIL")
    skipped = sum(1 for r in results if r[0] == "SKIP")
    print(f"\n{len(results) - failed - skipped} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
