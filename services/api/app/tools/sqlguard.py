"""Static guard for the manager agent's `query_data(sql)`.

The model writes SQL; before anything runs we require: exactly one SELECT, only the allow-listed views, no
function-in-FROM tricks (EXTERNAL_QUERY, ML.*), and a hard LIMIT. This is the first of several layers (a dry
run re-checks the tables BigQuery itself resolves, and the service account has no access to base tables).
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

# Views only: base tables hold ground truth (true_demand, conversations.gt_*) the agent must never see.
ALLOWED_VIEWS = frozenset({
    "v_sku_summary", "v_evidence", "v_assortment_gaps", "v_lost_revenue_today", "v_unmet_daily", "v_signals",
})
MAX_ROWS = 100
MAX_SQL_CHARS = 4000
_FORBIDDEN_FUNCS = {"EXTERNAL_QUERY", "SESSION_USER", "EXTERNAL_OBJECT_TRANSFORM"}


class SqlRejected(ValueError):
    """The query is not allowed; the message is safe to show to the model so it can rewrite the query."""


def validate_and_limit(sql: str, project: str, dataset: str, max_rows: int = MAX_ROWS) -> str:
    """Return the query to run (BigQuery dialect, LIMIT enforced) or raise `SqlRejected`."""
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise SqlRejected("empty query")
    if len(sql) > MAX_SQL_CHARS:
        raise SqlRejected(f"query too long (max {MAX_SQL_CHARS} characters)")
    try:
        statements = sqlglot.parse(sql, read="bigquery")
    except sqlglot.errors.SqlglotError as exc:
        raise SqlRejected(f"cannot parse SQL: {str(exc).splitlines()[0][:160]}") from None
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlRejected("exactly one statement is allowed")
    root = statements[0]
    if not isinstance(root, (exp.Select, exp.SetOperation)):
        raise SqlRejected("only SELECT queries are allowed")

    for node in root.walk():
        if isinstance(node, (exp.Command, exp.DDL, exp.DML, exp.Into, exp.Pragma, exp.Set, exp.Use)):
            raise SqlRejected("only SELECT queries are allowed")
        if isinstance(node, (exp.Anonymous, exp.Func)):
            name = (node.name or node.sql_name() or "").upper()
            if name in _FORBIDDEN_FUNCS:
                raise SqlRejected(f"function {name} is not allowed")

    ctes = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    for table in root.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise SqlRejected("table functions are not allowed in FROM")
        name = table.name.lower()
        if not table.args.get("db") and not table.args.get("catalog") and name in ctes:
            continue
        db = table.args.get("db")
        cat = table.args.get("catalog")
        if (cat and cat.name != project) or (db and db.name != dataset) or (cat and not db):
            raise SqlRejected(f"table {table.sql(dialect='bigquery')} is outside the {dataset} dataset")
        if name not in ALLOWED_VIEWS:
            raise SqlRejected(f"{name} is not available; query one of: {', '.join(sorted(ALLOWED_VIEWS))}")

    return _with_limit(root, max_rows).sql(dialect="bigquery")


def _with_limit(root: exp.Expression, max_rows: int) -> exp.Expression:
    if isinstance(root, exp.Select):
        limit = root.args.get("limit")
        n = None
        if limit is not None and isinstance(limit.expression, exp.Literal) and limit.expression.is_int:
            n = int(limit.expression.name)
        if n is not None and n <= max_rows:
            return root
        return root.limit(max_rows)
    return exp.select("*").from_(root.subquery("q")).limit(max_rows)  # UNION/INTERSECT: wrap
