"""Kiosk endpoints (docs/api-contract.md §3) with the shopper agent running on a scripted model."""
import uuid

from fastapi.testclient import TestClient

from app import main
from app.agents.runtime import AgentRuntime
from app.agents.shopper import build_shopper_agent

from .fake_llm import ScriptedLlm, call, say

SANDBOX = {"X-Sandbox-Id": str(uuid.uuid4())}


def kiosk_with(steps, monkeypatch):
    rt = AgentRuntime(build_shopper_agent(model=ScriptedLlm(steps)), app_name="api-test")
    monkeypatch.setattr(main, "_shopper_runtime", rt)
    return TestClient(main.app)


def new_session(c, store="S01", headers=SANDBOX):
    return c.post("/api/kiosk/sessions", json={"storeId": store}, headers=headers)


def test_out_of_stock_turn_returns_products_alternatives_and_branch(monkeypatch):
    c = kiosk_with(
        [call("search_products", query="santan kara 65 ml"),
         call("check_stock", store_id="S01", sku="SKU-0001"),
         call("find_alternatives", store_id="S01", sku="SKU-0001"),
         call("nearest_branch_with_stock", store_id="S01", sku="SKU-0001"),
         say("Maaf kak, santan Kara 65 ml kosong. Ada Sasa 65 ml, atau cek cabang BSD ya.")],
        monkeypatch,
    )
    sid = new_session(c).json()["sessionId"]
    r = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "santan kara kecil ada?"}, headers=SANDBOX)
    body = r.json()
    assert r.status_code == 200 and body["reply"].startswith("Maaf kak")
    assert body["products"] == [{"sku": "SKU-0001", "name": "Santan Kotak Kara 65 ml", "inStock": False,
                                 "aisle": "A1-2", "priceIdr": 4500, "stockQty": 0}]
    assert [a["sku"] for a in body["alternatives"]][0] == "SKU-0003"
    assert all(a["inStock"] and a["stockQty"] > 0 for a in body["alternatives"])
    assert body["nearestBranch"] == {"storeId": "S02", "name": "Radar Mart BSD", "distanceKm": 21.0, "stockQty": 40}


def test_in_stock_turn_has_no_alternatives_or_branch(monkeypatch):
    c = kiosk_with(
        [call("check_stock", store_id="S01", sku="SKU-0008"), say("Ada kak, Indomie stoknya 100, harganya Rp 3.200.")],
        monkeypatch,
    )
    sid = new_session(c).json()["sessionId"]
    body = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "indomie ada?"}, headers=SANDBOX).json()
    assert body["products"][0]["inStock"] is True and body["products"][0]["stockQty"] == 100
    assert body["alternatives"] == [] and body["nearestBranch"] is None


def test_unknown_store_is_404_in_the_uniform_error_format(monkeypatch):
    c = kiosk_with([], monkeypatch)
    r = new_session(c, store="S99")
    assert r.status_code == 404 and r.json()["error"]["code"] == "store_not_found"


def test_another_visitors_session_looks_like_a_missing_one(monkeypatch):
    c = kiosk_with([say("halo")], monkeypatch)
    sid = new_session(c).json()["sessionId"]
    other = {"X-Sandbox-Id": str(uuid.uuid4())}
    r = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "halo"}, headers=other)
    assert r.status_code == 404 and r.json()["error"]["code"] == "session_not_found"
    assert c.post("/api/kiosk/sessions/nope/messages", json={"text": "halo"}, headers=SANDBOX).status_code == 404


def test_image_and_audio_are_rejected_until_built(monkeypatch):
    c = kiosk_with([], monkeypatch)
    sid = new_session(c).json()["sessionId"]
    r = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "ini", "imageBase64": "AAAA"}, headers=SANDBOX)
    assert r.status_code == 400 and r.json()["error"]["code"] == "unsupported_input"


def test_empty_message_is_rejected(monkeypatch):
    c = kiosk_with([], monkeypatch)
    sid = new_session(c).json()["sessionId"]
    assert c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "  "}, headers=SANDBOX).status_code == 422


def test_conversation_continues_within_a_session(monkeypatch):
    c = kiosk_with([say("Halo kak!"), say("Siap kak.")], monkeypatch)
    sid = new_session(c).json()["sessionId"]
    r1 = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "halo"}, headers=SANDBOX).json()
    r2 = c.post(f"/api/kiosk/sessions/{sid}/messages", json={"text": "oke"}, headers=SANDBOX).json()
    assert (r1["reply"], r2["reply"]) == ("Halo kak!", "Siap kak.")
