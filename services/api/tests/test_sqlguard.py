import pytest

from app.tools.sqlguard import ALLOWED_VIEWS, MAX_ROWS, SqlRejected, validate_and_limit

P, D = "proj", "ds"


def ok(sql):
    return validate_and_limit(sql, P, D)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM v_sku_summary",
    "select sku from `proj.ds.v_sku_summary` where store_id = 'S01'",
    "SELECT a.sku FROM ds.v_unmet_daily a JOIN ds.v_sku_summary b USING (store_id, sku)",
    "WITH x AS (SELECT * FROM v_evidence) SELECT sku, COUNT(*) FROM x GROUP BY sku",
    "SELECT sku FROM v_sku_summary UNION ALL SELECT sku FROM v_evidence",
    "SELECT * FROM v_sku_summary;",
])
def test_allowed(sql):
    assert ok(sql).upper().count("LIMIT") == 1


@pytest.mark.parametrize("sql", [
    "SELECT * FROM conversations",
    "SELECT gt_sku FROM `proj.ds.conversations`",
    "SELECT * FROM true_demand",
    "SELECT * FROM pos_sales",
    "SELECT * FROM v_sku_summary, true_demand",
    "SELECT * FROM v_sku_summary WHERE sku IN (SELECT sku FROM true_demand)",
    "WITH x AS (SELECT * FROM conversations) SELECT * FROM x",
    "SELECT * FROM other.ds.v_sku_summary",
    "SELECT * FROM `proj.other_ds.v_sku_summary`",
    "SELECT * FROM `proj.ds.INFORMATION_SCHEMA.TABLES`",
    "SELECT * FROM EXTERNAL_QUERY('c', 'select 1')",
    "SELECT * FROM ML.PREDICT(MODEL m, TABLE v_sku_summary)",
])
def test_blocked_tables_and_functions(sql):
    with pytest.raises(SqlRejected):
        ok(sql)


@pytest.mark.parametrize("sql", [
    "DROP TABLE ds.pos_sales",
    "DELETE FROM v_sku_summary WHERE TRUE",
    "INSERT INTO v_signals SELECT * FROM v_signals",
    "UPDATE v_signals SET sku = 'x' WHERE TRUE",
    "CREATE TABLE t AS SELECT * FROM v_sku_summary",
    "SELECT 1; DROP TABLE x",
    "EXPORT DATA OPTIONS(uri='gs://b/*') AS SELECT * FROM v_sku_summary",
    "CALL ds.proc()",
    "",
    "   ",
    "SELEC oops",
])
def test_blocked_statements(sql):
    with pytest.raises(SqlRejected):
        ok(sql)


def test_limit_is_forced_or_lowered_never_raised():
    assert ok("SELECT * FROM v_sku_summary").endswith(f"LIMIT {MAX_ROWS}")
    assert ok("SELECT * FROM v_sku_summary LIMIT 5").endswith("LIMIT 5")
    assert ok("SELECT * FROM v_sku_summary LIMIT 100000").endswith(f"LIMIT {MAX_ROWS}")


def test_union_is_wrapped_so_the_limit_applies_to_the_whole_result():
    out = ok("SELECT sku FROM v_sku_summary UNION ALL SELECT sku FROM v_evidence")
    assert out.startswith("SELECT * FROM (") and out.endswith(f"LIMIT {MAX_ROWS}")


def test_oversized_query_is_rejected():
    with pytest.raises(SqlRejected, match="too long"):
        ok("SELECT * FROM v_sku_summary WHERE sku IN (" + ",".join("'x'" for _ in range(2000)) + ")")


def test_allowed_views_exclude_every_base_table():
    assert all(v.startswith("v_") for v in ALLOWED_VIEWS)
