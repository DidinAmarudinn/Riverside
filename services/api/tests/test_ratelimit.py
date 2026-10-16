import dataclasses
import uuid

from fastapi.testclient import TestClient

from app import main
from app.ratelimit import SlidingWindow

client = TestClient(main.app)


def sandbox():
    return {"X-Sandbox-Id": str(uuid.uuid4())}


def test_window_allows_up_to_the_limit_then_recovers():
    now = [0.0]
    w = SlidingWindow(clock=lambda: now[0])
    assert [w.retry_after("k", 3) for _ in range(3)] == [0, 0, 0]
    assert w.retry_after("k", 3) > 0
    now[0] = 61.0
    assert w.retry_after("k", 3) == 0


def test_limit_zero_disables_and_keys_are_independent():
    w = SlidingWindow()
    assert all(w.retry_after("k", 0) == 0 for _ in range(50))
    assert w.retry_after("a", 1) == 0 and w.retry_after("b", 1) == 0 and w.retry_after("a", 1) > 0


def patch(monkeypatch, **limits):
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, **limits))


def test_sandbox_limit_returns_429_with_retry_after_and_uniform_error(monkeypatch):
    patch(monkeypatch, rate_limit_sandbox=2)
    h = sandbox()
    sid = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=h).json()["sessionId"]
    codes = [client.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "santan"}, headers=h).status_code
             for _ in range(3)]
    assert codes == [200, 200, 429]
    r = client.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "santan"}, headers=h)
    assert r.json()["error"]["code"] == "rate_limited" and int(r.headers["Retry-After"]) >= 1
    other = sandbox()  # another visitor is unaffected
    sid2 = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=other).json()["sessionId"]
    assert client.post(f"/api/kiosk/sessions/{sid2}/messages", json={"text": "santan"}, headers=other).status_code == 200


def test_ip_limit_holds_when_the_sandbox_id_is_rotated(monkeypatch):
    patch(monkeypatch, rate_limit_ip=3)
    xff = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
    codes = []
    for _ in range(5):
        h = {**sandbox(), **xff}
        sid = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=h).json()["sessionId"]
        codes.append(client.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "santan"}, headers=h).status_code)
    assert codes == [200, 200, 200, 429, 429]


def test_instance_limit_is_the_spend_breaker(monkeypatch):
    patch(monkeypatch, rate_limit_instance=2)
    codes = []
    for i in range(4):
        h = {**sandbox(), "X-Forwarded-For": f"198.51.100.{i}"}  # all spoofed differently
        codes.append(client.post("/api/manager/S01/chat", json={"message": "ringkas"}, headers=h).status_code)
    assert codes == [200, 200, 429, 429]


def test_invalid_sandbox_is_still_400_not_429(monkeypatch):
    patch(monkeypatch, rate_limit_instance=1)
    assert client.post("/api/manager/S01/chat", json={"message": "x"}, headers={"X-Sandbox-Id": "nope"}).status_code == 400


def test_session_creation_is_limited_per_ip(monkeypatch):
    patch(monkeypatch, rate_limit_sessions_ip=2)
    codes = [client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=sandbox()).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
