import datetime as dt

from app.extract.sink import live_signal_doc, parse_ts

ROW = {
    "signal_id": "sig-1", "sandbox_id": "box", "store_id": "S01", "ts": "2026-10-15T04:06:19.488992+00:00",
    "requested_text": "ada santan kotak kecil?", "sku": "SKU-0001", "normalized_name": "santan kotak 65 ml",
    "outcome": "out_of_stock", "substitute_sku": None,
}


def test_parse_ts_returns_aware_datetime():
    assert parse_ts("2026-10-15T04:06:19Z") == dt.datetime(2026, 10, 15, 4, 6, 19, tzinfo=dt.timezone.utc)
    assert parse_ts("2026-10-15T04:06:19").tzinfo == dt.timezone.utc
    assert parse_ts("") is None and parse_ts(None) is None


def test_live_signal_doc_follows_contract():
    doc = live_signal_doc(ROW)
    assert isinstance(doc["ts"], dt.datetime)
    assert doc["matchedName"] == "Santan Kotak Kara 65 ml"
    assert doc["source"] == "Kiosk" and "substituteName" not in doc


def test_live_signal_doc_names_substitute_and_skips_unknown_sku():
    doc = live_signal_doc({**ROW, "sku": None, "substitute_sku": "SKU-0004", "ts": "bad"})
    assert "matchedName" not in doc
    assert doc["substituteName"] == "Santan Kotak Sasa 65 ml"
    assert not isinstance(doc["ts"], dt.datetime)  # server timestamp sentinel
