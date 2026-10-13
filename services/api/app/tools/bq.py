"""BigQuery access for the manager agent (read-only, dataset-scoped)."""


def run_readonly_query(sql: str) -> list[dict]:
    """Run a SELECT against the Demand Radar dataset."""
    raise NotImplementedError("wired to BigQuery later")
