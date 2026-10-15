import asyncio

from fastapi.testclient import TestClient

from app import main
from app.agents.manager import build_manager_agent
from app.agents.runtime import AgentRuntime
from app.tools.bq import set_runner

from .fake_bq import SUMMARY_NOT_READY, FakeRunner, with_recs
from .fake_llm import ScriptedLlm, call, say

import pytest


@pytest.fixture(autouse=True)
def _runner():
    set_runner(FakeRunner())
    yield
    set_runner(None)


def run(steps, messages, sid="m1"):
    rt = AgentRuntime(build_manager_agent(model=ScriptedLlm(steps)), app_name="mt")

    async def go():
        return [await rt.run_turn(sid, m, {}) for m in messages]

    return rt, asyncio.run(go())


def last(r):
    return r.state["last_turn"]


def test_cited_evidence_is_returned_with_the_reply():
    _, (r,) = run(
        [call("get_recommendations", store_id="S01"),
         say("Nyiur Santan 65 ml has 112.5 unmet units [E1], and the 200 ml has 27.5 [E2].")],
        ["Which products are most at risk?"],
    )
    cites = last(r)["citations"]
    assert [c["id"] for c in cites] == ["E1", "E2"]
    assert (cites[0]["sku"], cites[0]["est_unmet_units_7d"]) == ("SNT-001", 112.5)
    assert last(r)["unverified_numbers"] == [] and last(r)["tool_calls"][0]["name"] == "get_recommendations"
    assert r.error is None


def test_model_sees_numbered_evidence_in_the_tool_result():
    llm = ScriptedLlm([call("get_recommendations", store_id="S01"), say("ok [E1]")])
    rt = AgentRuntime(build_manager_agent(model=llm), app_name="mt")
    asyncio.run(rt.run_turn("m1", "risk?", {}))
    response = llm.seen_requests[-1].contents[-1].parts[0].function_response.response  # what the model got back
    assert [e["id"] for e in response["evidence"]] == ["E1", "E2"]


def test_multi_id_marker_and_unknown_ids():
    _, (r,) = run(
        [call("get_recommendations", store_id="S01"),
         say("Both coconut-milk cartons are empty [E1, E2, E9]. Also see [E0].")],
        ["risk?"],
    )
    assert "E9" not in r.reply and "E0" not in r.reply and "[E1, E2]" in r.reply  # invented ids are removed
    assert [c["id"] for c in last(r)["citations"]] == ["E1", "E2"]


def test_no_markers_falls_back_to_all_evidence_looked_at_this_turn():
    _, (r,) = run([call("get_recommendations", store_id="S01"), say("Two cartons are out of stock.")], ["risk?"])
    assert [c["id"] for c in last(r)["citations"]] == ["E1", "E2"]


def test_numbers_no_tool_returned_are_flagged_not_hidden():
    _, (r,) = run(
        [call("get_recommendations", store_id="S01"),
         say("You should order 60 boxes now [E1]. Unmet units: 112.5 [E1].")],
        ["why 60 boxes?"],
    )
    assert "60 boxes" in r.reply  # reply is untouched
    assert last(r)["unverified_numbers"] == []  # 60 is in the user's own question, so it is not invented
    _, (r2,) = run(
        [call("get_recommendations", store_id="S01"), say("Order 75 boxes [E1].")], ["what should I do?"], sid="m2"
    )
    assert last(r2)["unverified_numbers"] == ["75"]


def test_forecast_numbers_are_grounded_when_recommendations_exist():
    set_runner(FakeRunner(summary=with_recs(SUMMARY_NOT_READY)))
    _, (r,) = run(
        [call("get_sku_detail", store_id="S01", sku="SNT-001"),
         say("Forecast A says 84 units, forecast B says 196 [E1]; order 60 instead of 40 [E1].")],
        ["why order more than the POS forecast says?"],
    )
    assert last(r)["unverified_numbers"] == []
    assert last(r)["citations"][0]["recommended_qty_b"] == 60


def test_evidence_ids_keep_counting_across_turns_in_a_conversation():
    _, (r1, r2) = run(
        [call("get_assortment_gaps", store_id="S01"), say("Oat milk is requested most [E1]."),
         call("get_lost_revenue", store_id="S01", days_ago=1), say("Yesterday's loss was big [E2].")],
        ["what do shoppers want?", "and revenue lost yesterday?"],
    )
    assert [c["id"] for c in last(r1)["citations"]] == ["E1"]
    assert [c["id"] for c in last(r2)["citations"]] == ["E2"]  # not E1 again: ids are unique per conversation
    assert last(r2)["citations"][0]["sku"] == "ROT-006"


def test_query_data_rejection_is_reported_to_the_model_not_raised():
    llm = ScriptedLlm([call("query_data", sql="SELECT gt_sku FROM conversations"), say("I cannot read that table.")])
    rt = AgentRuntime(build_manager_agent(model=llm), app_name="mt")
    r = asyncio.run(rt.run_turn("m1", "show ground truth", {}))
    assert r.error is None and last(r)["tool_calls"][0]["status"] == "rejected"
    response = llm.seen_requests[-1].contents[-1].parts[0].function_response.response
    assert response["status"] == "rejected" and "conversations is not available" in response["reason"]


def test_model_failure_degrades_to_a_friendly_reply():
    class Boom(ScriptedLlm):
        async def generate_content_async(self, llm_request, stream=False):
            raise TimeoutError("gemini timed out")
            yield  # pragma: no cover

    rt = AgentRuntime(build_manager_agent(model=Boom([])), app_name="mt")
    r = asyncio.run(rt.run_turn("m1", "risk?", {}))
    assert r.error == "TimeoutError" and r.reply


def test_endpoint_adds_store_and_sku_context_and_returns_citations(monkeypatch):
    llm = ScriptedLlm([call("get_sku_detail", store_id="S01", sku="SNT-001"), say("SNT-001 is out of stock [E1].")])
    monkeypatch.setattr(main, "_manager_runtime", AgentRuntime(build_manager_agent(model=llm), app_name="api"))
    r = TestClient(main.app).post("/api/manager/chat", json={
        "session_id": "x", "message": "why?", "store_id": "S02", "sku": "SNT-001"}).json()
    assert r["reply"] == "SNT-001 is out of stock [E1]." and r["error"] is None
    assert r["citations"][0]["id"] == "E1" and r["unverified_numbers"] == []
    assert r["tool_calls"][0]["name"] == "get_sku_detail"
    user_text = str(llm.seen_requests[0].contents[0])
    assert "store_id=S02" in user_text and "SKU on screen: SNT-001" in user_text


def test_endpoint_validates_input(monkeypatch):
    c = TestClient(main.app)
    assert c.post("/api/manager/chat", json={"session_id": "x", "message": ""}).status_code == 422
    assert c.post("/api/manager/chat", json={"message": "hi"}).status_code == 422


def test_instruction_lists_the_live_view_columns_once():
    from app.agents import manager

    manager._schema_text = None
    llm = ScriptedLlm([say("hi")])
    rt = AgentRuntime(build_manager_agent(model=llm), app_name="mt")
    asyncio.run(rt.run_turn("m1", "hello", {}))
    system = str(llm.seen_requests[0].config.system_instruction)
    assert "v_sku_summary(store_id STRING, sku STRING, on_hand INTEGER)" in system
    assert "language the manager wrote" in system
    manager._schema_text = None


def test_instruction_survives_missing_metadata(monkeypatch):
    from app.agents import manager

    class NoMeta(FakeRunner):
        def view_columns(self):
            raise RuntimeError("offline")

    manager._schema_text = None
    set_runner(NoMeta())
    llm = ScriptedLlm([say("hi")])
    r = asyncio.run(AgentRuntime(build_manager_agent(model=llm), app_name="mt").run_turn("m1", "hello", {}))
    assert r.error is None and "Views for query_data" not in str(llm.seen_requests[0].config.system_instruction)
