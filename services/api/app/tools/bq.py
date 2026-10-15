"""BigQuery access for the manager agent: parametrised queries for the fixed tools, guarded free-form SQL
for `query_data`."""
from __future__ import annotations

import datetime as dt
import decimal
import logging
from typing import Any

from ..config import settings
from .sqlguard import ALLOWED_VIEWS, SqlRejected, validate_and_limit

log = logging.getLogger(__name__)

MAX_BYTES_BILLED = 100_000_000   # 100 MB per query: the views scan a few MB; a runaway cross join cannot
TIMEOUT_S = 30
MAX_CELL_CHARS = 300             # transcripts and quotes are cut so one row cannot flood the model


def clean(value: Any) -> Any:
    """BigQuery value -> JSON-safe, compact value."""
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat(sep=" ", timespec="seconds") if isinstance(value, dt.datetime) else value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
        return value[:MAX_CELL_CHARS] + "..."
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def clean_row(row: dict) -> dict:
    return {k: clean(v) for k, v in row.items()}


class BqRunner:
    def __init__(self, project: str, dataset: str, client=None, agent_client=None,
                 max_bytes: int = MAX_BYTES_BILLED, timeout_s: int = TIMEOUT_S):
        if client is None:
            from google.cloud import bigquery

            client = bigquery.Client(project=project)
        self.project, self.dataset = project, dataset
        self.fq = f"`{project}.{dataset}`"
        self._client = client
        self._agent_client = agent_client or client
        self._max_bytes, self._timeout = max_bytes, timeout_s
        self._lineage: set[str] | None = None
        self._columns: dict[str, list[str]] | None = None

    def _config(self, params: dict | None = None, dry_run: bool = False):
        from google.cloud import bigquery

        qp = []
        for name, value in (params or {}).items():
            kind = "INT64" if isinstance(value, int) and not isinstance(value, bool) else \
                   "FLOAT64" if isinstance(value, float) else "STRING"
            qp.append(bigquery.ScalarQueryParameter(name, kind, value))
        return bigquery.QueryJobConfig(
            query_parameters=qp, maximum_bytes_billed=self._max_bytes, dry_run=dry_run,
            use_query_cache=not dry_run, default_dataset=f"{self.project}.{self.dataset}",
        )

    def rows(self, sql: str, params: dict | None = None) -> list[dict]:
        """Run a fixed, parametrised query as the API's own identity."""
        job = self._client.query(sql, job_config=self._config(params))
        return [clean_row(dict(r)) for r in job.result(timeout=self._timeout)]

    def agent_dry_run(self, sql: str) -> dict:
        job = self._agent_client.query(sql, job_config=self._config(dry_run=True))
        return {
            "statement_type": job.statement_type,
            "tables": {t.table_id for t in (job.referenced_tables or [])},
            "bytes": job.total_bytes_processed or 0,
        }

    def allowed_lineage(self) -> set[str]:
        """Base tables that the allow-listed views read from (BigQuery's dry run reports these, not the views).

        A query touching any table outside this set (e.g. `true_demand`) is rejected even if the SQL parser
        was fooled. Computed once from dry runs of `SELECT * FROM <view>`.
        """
        if self._lineage is None:
            tables: set[str] = set()
            for view in sorted(ALLOWED_VIEWS):
                tables |= self.agent_dry_run(f"SELECT * FROM {self.fq}.{view}")["tables"]
            self._lineage = tables
        return self._lineage

    def view_columns(self) -> dict[str, list[str]]:
        """`{view: ["col TYPE", ...]}` for the allowed views, from table metadata (cached; no query is run)."""
        if self._columns is None:
            cols = {}
            for view in sorted(ALLOWED_VIEWS):
                table = self._client.get_table(f"{self.project}.{self.dataset}.{view}")
                cols[view] = [f"{f.name} {f.field_type}" for f in table.schema]
            self._columns = cols
        return self._columns

    def agent_rows(self, sql: str) -> list[dict]:
        job = self._agent_client.query(sql, job_config=self._config())
        return [clean_row(dict(r)) for r in job.result(timeout=self._timeout)]


_override: BqRunner | None = None
_runner: BqRunner | None = None


def set_runner(runner: BqRunner | None) -> None:
    """Inject a runner (tests, scripted demos). None restores the configured one."""
    global _override
    _override = runner


def get_runner() -> BqRunner:
    global _runner
    if _override is not None:
        return _override
    if _runner is None:
        client = agent_client = None
        if settings.agent_sql_sa:
            agent_client = _impersonated_client(settings.gcp_project, settings.agent_sql_sa)
        _runner = BqRunner(settings.gcp_project, settings.bq_dataset, agent_client=agent_client)
    return _runner


def _impersonated_client(project: str, service_account: str):
    import google.auth
    from google.auth import impersonated_credentials
    from google.cloud import bigquery

    source, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds = impersonated_credentials.Credentials(
        source_credentials=source, target_principal=service_account,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=project, credentials=creds)


def run_readonly_query(sql: str, runner: BqRunner | None = None) -> dict:
    """Validate, dry-run and run a model-written SELECT. Never raises: problems come back as a status."""
    runner = runner or get_runner()
    try:
        safe_sql = validate_and_limit(sql, runner.project, runner.dataset)
        dry = runner.agent_dry_run(safe_sql)
        if dry["statement_type"] not in (None, "SELECT"):
            raise SqlRejected("only SELECT queries are allowed")
        outside = dry["tables"] - runner.allowed_lineage()
        if outside:  # BigQuery resolved a table our parser did not see
            raise SqlRejected(f"tables not available: {', '.join(sorted(outside))}")
        if dry["bytes"] > runner._max_bytes:
            raise SqlRejected(f"query would scan {dry['bytes'] / 1e6:.0f} MB (limit {runner._max_bytes / 1e6:.0f} MB)")
        rows = runner.agent_rows(safe_sql)
    except SqlRejected as exc:
        return {"status": "rejected", "reason": str(exc)}
    except Exception as exc:  # BigQuery rejected it (bad column, timeout, ...): let the model fix the query
        log.warning("query_data failed: %s", exc)
        return {"status": "error", "message": _error_text(exc)}
    columns = list(rows[0]) if rows else []
    return {
        "status": "ok", "columns": columns, "rows": rows, "row_count": len(rows),
        "truncated": len(rows) >= 100,
        "evidence": [{"type": "query", "sql": safe_sql, "row_count": len(rows)}],
    }


def _error_text(exc: Exception) -> str:
    errors = getattr(exc, "errors", None)
    if errors and isinstance(errors[0], dict) and errors[0].get("message"):
        return str(errors[0]["message"])[:300]
    return str(exc).splitlines()[0][:300]


def query_data(sql: str) -> dict:
    """Run a read-only SQL query against the Demand Radar views and return the rows.

    Use it for anything the other tools do not cover (custom filters, totals, comparisons). Only SELECT is
    allowed, only these views: v_sku_summary (per store+SKU status: stock, sales, stockouts, unmet demand,
    forecast and recommendation), v_unmet_daily (per day: sold, stock, stockout flag, unmet signals),
    v_evidence (shopper requests with text and outcome), v_assortment_gaps (products shoppers ask for that the
    store does not carry), v_lost_revenue_today, v_signals. Results are capped at 100 rows. Do the math in
    SQL (SUM, COUNT, ...) instead of computing in your head.

    Args:
        sql: One BigQuery Standard SQL SELECT statement.

    Returns:
        {status: "ok" | "rejected" | "error", columns, rows, row_count} (or `reason`/`message` on failure).
    """
    return run_readonly_query(sql)
