import app.extract.client as client
from app import main
from app.extract.catalog import load_catalog

CONV = {"conversation_id": "c1", "transcript": '[{"role": "shopper", "text": "ada santan kotak kecil?"}]'}


def test_live_gemini_failure_falls_back_to_rules(monkeypatch):
    def boom(*_, **__):
        raise TimeoutError("gemini took too long")

    monkeypatch.setattr(client, "extract_item", boom)
    monkeypatch.setattr(client, "live_client", lambda: object())
    assert main._gemini_item(CONV, load_catalog()) is None


def test_live_gemini_is_one_call_without_thinking(monkeypatch):
    seen = {}

    def fake(_client, model, transcript, catalog, retries, thinking_budget):
        seen.update(retries=retries, thinking_budget=thinking_budget)
        return {"sku": "SKU-0001", "confidence": 0.9}

    monkeypatch.setattr(client, "extract_item", fake)
    monkeypatch.setattr(client, "live_client", lambda: object())
    assert main._gemini_item(CONV, load_catalog())["sku"] == "SKU-0001"
    assert seen == {"retries": 1, "thinking_budget": 0}


def _run(monkeypatch, transcript, gemini):
    import dataclasses
    import json

    from app.extract import sink

    calls, written = [], []
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, backend="gcp", live_extract_llm=True))
    monkeypatch.setattr(main, "_gemini_item", lambda conv, cat: calls.append(1) or gemini)
    monkeypatch.setattr(sink, "write_signal", written.append)
    main.process_pubsub_message({"conversationId": "c2", "sandboxId": "b", "storeId": "S01", "turn": 1,
                                 "transcript": json.dumps(transcript)})
    return calls, written[0]


def test_clear_chats_skip_gemini(monkeypatch):
    calls, row = _run(monkeypatch, [{"role": "shopper", "text": "ada santan kotak kara 65 ml?"},
                                    {"role": "agent", "text": "Santan Kotak Kara 65 ml lagi kosong nih kak."}], None)
    assert calls == [] and row["sku"] == "SKU-0001" and row["model_version"].endswith("-rules")


def test_unsure_chats_ask_gemini(monkeypatch):
    calls, row = _run(monkeypatch, [{"role": "shopper", "text": "min ada roit? dong"},
                                    {"role": "agent", "text": "Ada kak. Roti Tawar Jumbo Sari Roti 1 pack ada di rak I1-4."}],
                      {"sku": "SKU-0115", "confidence": 0.9, "qty": 1})
    assert calls == [1] and row["sku"] == "SKU-0115" and row["outcome"] == "purchased"
    assert row["model_version"].endswith("-gemini") and row["turn"] == 1


def test_each_product_in_a_chat_is_its_own_signal(monkeypatch):
    import dataclasses
    import json

    from app.extract import sink

    written = []
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, backend="gcp", live_extract_llm=False))
    monkeypatch.setattr(sink, "write_signal", written.append)
    chat = [{"role": "shopper", "text": "mau beli minyak bimoli"},
            {"role": "agent", "text": "Ada kak, Minyak Goreng Bimoli 1 L di rak A2-3."},
            {"role": "shopper", "text": "ada santan kotak kara 65 ml?"},
            {"role": "agent", "text": "Santan Kotak Kara 65 ml lagi kosong nih kak."}]
    base = {"conversationId": "c3", "sandboxId": "b", "storeId": "S01"}
    main.process_pubsub_message({**base, "turn": 1, "request": 0, "requestStart": 0, "transcript": chat[:2]})
    main.process_pubsub_message({**base, "turn": 2, "request": 1, "requestStart": 2, "transcript": chat})
    first, second = written
    assert first["signal_id"] == "sig-c3" and first["outcome"] == "purchased"
    assert second["signal_id"] == "sig-c3-1" and second["sku"] == "SKU-0001" and second["outcome"] == "out_of_stock"
    assert second["requested_text"] == "ada santan kotak kara 65 ml?"
