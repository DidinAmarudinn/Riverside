"""Storage interface behind the agent tools.

Tools never read CSVs or call BigQuery directly; they go through a `Repository`. `LocalRepo` serves dev and
tests from `data/` (simulator output + in-memory live stock). A BigQuery/Firestore implementation plugs in
behind the same interface when `DATA_BACKEND=gcp`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from ..config import settings


class Repository(Protocol):
    def products(self) -> list[dict]:
        """All SKUs in the product master."""

    def get_product(self, sku: str) -> dict | None: ...

    def stores(self) -> list[dict]:
        """`[{id, name}]` for every branch."""

    def get_store(self, store_id: str) -> dict | None: ...

    def distance_km(self, a: str, b: str) -> float | None:
        """Road distance between two branches, None when unknown."""

    def get_stock(self, store_id: str, sku: str) -> int | None:
        """Live on-hand units, None when the store/SKU pair is unknown."""

    def stock_by_store(self, sku: str) -> dict[str, int]:
        """Live on-hand units of one SKU in every branch."""

    def set_stock(self, store_id: str, sku: str, units: int) -> None:
        """Demo/sandbox: overwrite live stock (restock, empty the shelf)."""

    def reset_live_stock(self) -> None:
        """Restore the demo starting state (hero scenario: shelf empty)."""


_override: Repository | None = None


def set_repo(repo: Repository | None) -> None:
    """Inject a repository (tests, scripted demos). Pass None to go back to the configured backend."""
    global _override
    _override = repo


@lru_cache(maxsize=1)
def _configured_repo() -> Repository:
    if settings.backend == "local":
        from .local import LocalRepo

        return LocalRepo(settings.data_dir)
    if settings.backend == "gcp":
        from .gcp import GcpRepo

        return GcpRepo(settings.gcp_project, settings.bq_dataset)
    raise ValueError(f"unknown DATA_BACKEND {settings.backend!r} (use 'local' or 'gcp')")


def get_repo() -> Repository:
    return _override or _configured_repo()


def reset_repo_cache() -> None:
    _configured_repo.cache_clear()
