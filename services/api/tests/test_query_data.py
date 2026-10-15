import datetime as dt
import decimal

from app.tools import bq
from app.tools.bq import BqRunner, clean, query_data, run_readonly_query, set_runner

from .fake_bq import FakeRunner


def test_ok_returns_rows_and_query_evidence():
    r = run_readonly_query("SELECT COUNT(*) AS n FROM v_sku_summary", FakeRunner())
    assert r["status"] == "ok" and r["rows"] == [{"n": 1}] and r["columns"] == ["n"]
    assert r["evidence"][0]["type"] == "query" and r["evidence"][0]["sql"].endswith("LIMIT 100")


def test_the_executed_sql_has_the_forced_limit():
    fake = FakeRunner()
    run_readonly_query("SELECT * FROM v_sku_summary", fake)
    assert fake.agent_sql == ["SELECT * FROM v_sku_summary LIMIT 100"]


def test_parser_rejection_never_reaches_bigquery():
    fake = FakeRunner()
    r = run_readonly_query("SELECT gt_sku FROM conversations", fake)
    assert r["status"] == "rejected" and fake.agent_sql == []


def test_dry_run_catches_a_table_outside_the_view_lineage():
    fake = FakeRunner(dry={"statement_type": "SELECT", "tables": {"true_demand"}, "bytes": 10})
    r = run_readonly_query("SELECT * FROM v_sku_summary", fake)
    assert r["status"] == "rejected" and "true_demand" in r["reason"]


def test_dry_run_statement_type_and_bytes_are_enforced():
    r = run_readonly_query("SELECT 1 FROM v_sku_summary", FakeRunner(dry={"statement_type": "DELETE", "tables": set(), "bytes": 0}))
    assert r["status"] == "rejected"
    r = run_readonly_query("SELECT 1 FROM v_sku_summary", FakeRunner(dry={"statement_type": "SELECT", "tables": set(), "bytes": 9_999_999_999}))
    assert r["status"] == "rejected" and "scan" in r["reason"]


def test_bigquery_errors_come_back_as_status_not_exceptions():
    r = run_readonly_query("SELECT nope FROM v_sku_summary", FakeRunner(agent_error=RuntimeError("Unrecognized name: nope\nJob ID: x")))
    assert r["status"] == "error" and r["message"] == "Unrecognized name: nope"


def test_query_data_tool_uses_the_active_runner():
    set_runner(FakeRunner(agent_result=[{"store_id": "S01", "n": 3}]))
    try:
        assert query_data("SELECT store_id, 3 AS n FROM v_sku_summary")["rows"] == [{"store_id": "S01", "n": 3}]
    finally:
        set_runner(None)


def test_clean_makes_values_json_safe_and_compact():
    assert clean(dt.date(2026, 10, 14)) == "2026-10-14"
    assert clean(dt.datetime(2026, 10, 14, 11, 44, 44)) == "2026-10-14 11:44:44"
    assert clean(decimal.Decimal("1.5")) == 1.5 and clean(112.5000001) == 112.5
    assert clean("x" * 1000).endswith("...") and len(clean("x" * 1000)) < 400
    assert clean(["a", 1.234]) == ["a", 1.23]


class _Job:
    statement_type = "SELECT"
    referenced_tables = []
    total_bytes_processed = 0

    def result(self, timeout=None):
        return [{"d": dt.date(2026, 10, 14), "x": decimal.Decimal("2.5")}]


class _Client:
    def __init__(self):
        self.seen = []

    def query(self, sql, job_config=None):
        self.seen.append((sql, job_config))
        return _Job()


def test_runner_passes_typed_parameters_a_byte_cap_and_the_default_dataset():
    client = _Client()
    runner = BqRunner("proj", "ds", client=client, max_bytes=777)
    rows = runner.rows("SELECT 1 WHERE a = @a AND b = @b AND c = @c", {"a": "S01", "b": 7, "c": 1.5})
    cfg = client.seen[0][1]
    assert {(p.name, p.type_, p.value) for p in cfg.query_parameters} == {
        ("a", "STRING", "S01"), ("b", "INT64", 7), ("c", "FLOAT64", 1.5)}
    assert cfg.maximum_bytes_billed == 777 and (cfg.default_dataset.project, cfg.default_dataset.dataset_id) == ("proj", "ds")
    assert rows == [{"d": "2026-10-14", "x": 2.5}]


def test_lineage_is_computed_once_from_dry_runs_of_the_allowed_views():
    client = _Client()
    runner = BqRunner("proj", "ds", client=client)
    runner.allowed_lineage()
    n = len(client.seen)
    runner.allowed_lineage()
    from app.tools.sqlguard import ALLOWED_VIEWS

    assert n == len(ALLOWED_VIEWS) == 5 and len(client.seen) == n  # one dry run per allowed view, then cached
