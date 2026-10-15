from fastapi.testclient import TestClient

from app import main
from app.agents.runtime import AgentRuntime
from app.agents.shopper import build_shopper_agent

from .fake_llm import ScriptedLlm, call, say


def client_with(steps, monkeypatch):
    rt = AgentRuntime(build_shopper_agent(model=ScriptedLlm(steps)), app_name="api-test")
    monkeypatch.setattr(main, "_shopper_runtime", rt)
    return TestClient(main.app)


def test_chat_returns_reply_signal_and_tool_calls(world, publisher, monkeypatch):
    c = client_with(
        [call("search_products", query="santan kara 65 ml"),
         call("check_stock", store_id="S01", sku="SKU-0001"),
         say("Maaf kak, santan kara 65 ml lagi kosong. Mau coba ukuran lain?")],
        monkeypatch,
    )
    r = c.post("/api/shopper/chat", json={"session_id": "abc", "store_id": "S01", "message": "santan kara kecil ada?"})
    body = r.json()
    assert r.status_code == 200 and body["reply"].startswith("Maaf kak")
    assert body["signal"] == {"conversation_id": "abc", "turn": 1, "logged": True}
    assert [t["name"] for t in body["tool_calls"]] == ["search_products", "check_stock"]
    assert body["error"] is None


def test_unknown_store_is_404(world, monkeypatch):
    c = client_with([], monkeypatch)
    r = c.post("/api/shopper/chat", json={"session_id": "abc", "store_id": "S99", "message": "halo"})
    assert r.status_code == 404


def test_empty_message_is_rejected(world, monkeypatch):
    c = client_with([], monkeypatch)
    assert c.post("/api/shopper/chat", json={"session_id": "abc", "message": ""}).status_code == 422
