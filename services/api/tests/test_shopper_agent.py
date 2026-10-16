import asyncio

import pytest

from app.agents import guards
from app.agents.runtime import AgentRuntime
from app.agents.shopper import build_shopper_agent

from .fake_llm import ScriptedLlm, call, say

STATE = {"store_id": "S01", "store_name": "Radar Mart Cipete"}


def run(steps, messages, sid="s1"):
    llm = ScriptedLlm(steps)
    rt = AgentRuntime(build_shopper_agent(model=llm), app_name="t")

    async def go():
        return [await rt.run_turn(sid, m, STATE) for m in messages]

    return rt, llm, asyncio.run(go())


def test_in_stock_answer_is_grounded_and_logged(world, publisher):
    _, _, (r,) = run(
        [call("search_products", query="minyak goreng bimoli"),
         call("check_stock", store_id="S01", sku="SKU-0005"),
         say("Ada kak, Minyak Goreng Bimoli 2 L stoknya 30, harganya Rp 37.000. Letaknya di rak A2-1.")],
        ["ada minyak bimoli 2 liter?"],
    )
    assert r.reply.startswith("Ada kak") and "Rp 37.000" in r.reply and r.error is None
    assert [c["name"] for c in r.tool_calls] == ["search_products", "check_stock"]
    assert r.logged and r.turn == 1
    (ev,) = publisher.recent()
    assert ev.conversation_id == "s1" and ev.store_id == "S01" and ev.turn == 1 and ev.channel == "chat"
    assert ev.transcript[0] == {"role": "shopper", "text": "ada minyak bimoli 2 liter?"}
    assert [c["name"] for c in ev.tool_calls] == ["search_products", "check_stock"]
    assert ev.tool_calls[1]["result"]["units"] == 30  # grounded result travels with the event


def test_invented_stock_is_replaced_and_counted(world, publisher):
    rt, _, (r,) = run([say("Ada kak, stoknya 99 biji, harganya Rp 1.000.")], ["ada santan?"])
    assert r.reply == guards.FALLBACK_REPLY
    session = asyncio.run(rt.sessions.get_session(app_name="t", user_id="kiosk", session_id="s1"))
    assert session.state["guard_violations"] == 1
    assert publisher.recent()[0].transcript[-1]["text"] == guards.FALLBACK_REPLY  # logged what was actually said


def test_wrong_store_id_from_model_is_overridden(world, publisher):
    _, _, (r,) = run(
        [call("check_stock", store_id="S02", sku="SKU-0001"),  # model tries BSD; shopper stands in Cipete
         say("Maaf kak, stoknya lagi kosong di sini.")],
        ["santan kara ada?"],
    )
    result = publisher.recent()[0].tool_calls[0]["result"]
    assert result["store_id"] == "S01" and result["status"] == "out_of_stock"


def test_reply_is_capped_at_three_sentences(world, publisher):
    _, _, (r,) = run([say("Satu kak. Dua kak. Tiga kak. Empat kak. Lima kak.")], ["halo"])
    assert r.reply == "Satu kak. Dua kak. Tiga kak."


def test_not_stocked_request_is_still_logged(world, publisher):
    _, _, (r,) = run(
        [call("search_products", query="oat milk"),
         say("Maaf kak, oat milk belum kami jual. Permintaannya aku catat ya.")],
        ["ada oat milk?"],
    )
    assert r.logged
    assert publisher.recent()[0].tool_calls[0]["result"]["status"] == "no_match"


def test_second_turn_extends_the_same_conversation(world, publisher):
    _, _, (r1, r2) = run(
        [say("Halo kak, mau cari apa?"), say("Oke kak, ditunggu ya.")], ["halo", "nanti aja"]
    )
    assert (r1.turn, r2.turn) == (1, 2)
    last = publisher.recent()[0]
    assert last.turn == 2 and len(last.transcript) == 4
    assert [t["role"] for t in last.transcript] == ["shopper", "agent", "shopper", "agent"]


def test_number_from_shoppers_own_message_is_allowed(world, publisher):
    _, _, (r,) = run([say("Siap kak, dicatat butuh 3 pcs ya.")], ["aku butuh 3 pcs"])
    assert r.reply == "Siap kak, dicatat butuh 3 pcs ya."


def test_publish_failure_does_not_break_chat(world, monkeypatch):
    class Broken:
        def publish(self, event):
            raise RuntimeError("pubsub down")

    monkeypatch.setattr("app.agents.shopper.get_publisher", lambda: Broken())
    _, _, (r,) = run([say("Halo kak!")], ["halo"])
    assert r.reply == "Halo kak!" and r.error is None and not r.logged


def test_model_failure_degrades_to_friendly_reply(world, publisher):
    class Boom(ScriptedLlm):
        async def generate_content_async(self, llm_request, stream=False):
            raise TimeoutError("gemini timed out")
            yield  # pragma: no cover

    rt = AgentRuntime(build_shopper_agent(model=Boom([])), app_name="t")
    r = asyncio.run(rt.run_turn("s1", "halo", STATE))
    assert r.error == "TimeoutError" and "Maaf kak" in r.reply
    assert publisher.recent() == []  # nothing half-logged


def test_instruction_names_the_store(world, publisher):
    _, llm, _ = run([say("Halo kak!")], ["halo"])
    system = llm.seen_requests[0].config.system_instruction
    assert "Radar Mart Cipete" in str(system) and "store_id: S01" in str(system)


def test_promise_to_search_without_a_tool_triggers_the_search(world, publisher):
    rt, _, (r,) = run(
        [say("Siap kak, saya carikan dulu ya."),  # model "promises" instead of calling a tool
         call("check_stock", store_id="S01", sku="SKU-0007"),
         say("Ada kak, telurnya stok 15, harganya Rp 28.000.")],
        ["telor ayam ada?"],
    )
    assert [c["name"] for c in r.tool_calls] == ["search_products", "check_stock"]
    assert r.tool_calls[0]["args"] == {"query": "telor ayam ada?"}
    assert "stok 15" in r.reply
    session = asyncio.run(rt.sessions.get_session(app_name="t", user_id="kiosk", session_id="s1"))
    assert session.state["promise_searches"] == 1


def test_waiting_phrase_after_a_tool_call_is_left_alone(world, publisher):
    _, _, (r,) = run(
        [call("search_products", query="oat milk"), say("Maaf kak, oat milk belum ada. Sebentar lagi mungkin ya.")],
        ["ada oat milk?"],
    )
    assert [c["name"] for c in r.tool_calls] == ["search_products"]  # no extra injected search


def test_thinking_is_off_by_default_for_both_agents(world, publisher):
    from app.agents.manager import build_manager_agent
    from app.tools.bq import set_runner

    from .fake_bq import FakeRunner

    for build in (build_shopper_agent, build_manager_agent):
        set_runner(FakeRunner())
        llm = ScriptedLlm([say("halo")])
        rt = AgentRuntime(build(model=llm), app_name="t")
        asyncio.run(rt.run_turn("s1", "halo", {"store_id": "S01", "store_name": "Radar Mart Cipete"}))
        assert llm.seen_requests[0].config.thinking_config.thinking_budget == 0
    set_runner(None)


def test_negative_budget_leaves_thinking_to_the_model(monkeypatch):
    from dataclasses import replace

    from app.agents import llm as llm_mod

    monkeypatch.setattr(llm_mod, "settings", replace(llm_mod.settings, gemini_thinking_budget=-1))
    assert llm_mod.thinking_planner() is None


def test_a_new_product_search_starts_a_new_request(world, publisher):
    _, _, _ = run(
        [call("search_products", query="minyak"), say("Ada kak, Minyak Goreng Bimoli 1 L di rak A2-3."),
         call("search_products", query="santan"), say("Ada kak, Santan Kotak Kara 1 L di rak A1-4."),
         say("Siap kak.")],
        ["mau beli minyak", "apakah ada santan", "oke makasih"],
    )
    third, second, first = publisher.recent()[:3]
    assert (first.request, first.request_start) == (0, 0)
    assert (second.request, second.request_start) == (1, 2)  # santan starts at its own shopper message
    assert (third.request, third.request_start) == (1, 2)  # a follow-up without a search stays with santan
    assert '"requestStart": 2' in second.to_json()


def test_chit_chat_before_the_first_search_is_not_a_request(world, publisher):
    _, _, _ = run(
        [say("Halo kak, mau cari apa?"), call("search_products", query="santan"), say("Ada kak.")],
        ["halo", "ada santan?"],
    )
    ev = publisher.recent()[0]
    assert (ev.request, ev.request_start) == (0, 2)
