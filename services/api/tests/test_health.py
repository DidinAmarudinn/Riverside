import uuid

from fastapi.testclient import TestClient

from app.extract.schema import ExtractedItem, Outcome, decide_outcome
from app.main import app

client = TestClient(app)
SANDBOX = {"X-Sandbox-Id": str(uuid.uuid4())}


def test_healthz():
    r = client.get("/api/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_sandbox_header_required_and_validated():
    for headers in ({}, {"X-Sandbox-Id": "not-a-uuid"}, {"X-Sandbox-Id": str(uuid.uuid1())}):
        r = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=headers)
        assert r.status_code == 400
        assert r.json() == {"error": {"code": "invalid_sandbox_id", "message": "invalid_sandbox_id"}}


def test_kiosk_message_shape():
    session = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers=SANDBOX).json()["sessionId"]
    r = client.post(f"/api/kiosk/sessions/{session}/messages", json={"text": "ada santan kotak kecil?"}, headers=SANDBOX)
    assert r.status_code == 200
    assert {"reply", "products", "alternatives", "nearestBranch"} <= r.json().keys()


def test_manager_response_shapes():
    # docs/api-contract.md §3.1; the web app validates these with zod.
    overview = client.get("/api/manager/S01/overview", headers=SANDBOX).json()
    assert {"storeId", "kpis", "topRisks"} <= overview.keys()
    assert {"lostRevenueToday", "unmetToday", "stockoutSkus"} <= overview["kpis"].keys()
    assert "items" in client.get("/api/manager/S01/recommendations", headers=SANDBOX).json()
    sku = client.get("/api/manager/S01/sku/SKU-0001", headers=SANDBOX).json()
    assert {"product", "riskType", "kpis", "sales", "forecastA", "forecastB", "unmetDaily", "evidence",
            "reason"} <= sku.keys()
    assert {"total", "items"} <= sku["evidence"].keys()
    assert {"recommendedQtyA", "recommendedQtyB", "reasonText"} <= sku["reason"].keys()
    assert "items" in client.get("/api/manager/S01/gaps", headers=SANDBOX).json()
    chat = client.post("/api/manager/S01/chat", json={"message": "Why 60?"}, headers=SANDBOX).json()
    assert {"reply", "citations", "sessionId"} <= chat.keys()


def test_demo_reset_is_204():
    assert client.post("/api/demo/reset", headers=SANDBOX).status_code == 204


def test_pubsub_extract_rejects_missing_or_bad_token():
    assert client.post("/pubsub/extract", content=b"not json").status_code == 401
    r = client.post("/pubsub/extract", json={"message": {}}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_errors_use_uniform_format():
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and set(r.json()["error"]) == {"code", "message"}


def item(**kw):
    base = dict(requested_text="santen kotak kcl", sku="SKU-0001", normalized_name="Santan Kotak 65 ml",
                category="Cooking Essentials", intent="ask_availability", confidence=0.9)
    return ExtractedItem(**{**base, **kw})


def test_outcome_rules():
    assert decide_outcome(item(), stock_on_hand=0) == Outcome.out_of_stock
    assert decide_outcome(item(), stock_on_hand=12) == Outcome.purchased
    assert decide_outcome(item(accepted_substitute="SKU-0002"), stock_on_hand=0) == Outcome.substituted
    assert decide_outcome(item(sku=None), stock_on_hand=None) == Outcome.not_carried
    assert decide_outcome(item(confidence=0.5), stock_on_hand=0) == Outcome.low_confidence
