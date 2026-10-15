"""Manager-agent tools over the Demand Radar views (all queries parametrised, read-only).

Every tool returns `evidence` items (SKU metrics, shopper quotes, gaps). The agent callback numbers them E1, E2,
... and the model must cite them, so the UI can link each claim to its evidence.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .bq import get_runner

_SUMMARY_COLS = (
    "store_id, sku, name, category, aisle, price_idr, on_hand, is_stockout_today, sold_7d, sold_28d, "
    "avg_daily_sold_instock_28d, stockout_days_7d, stockout_days_28d, unmet_signals_7d, est_unmet_units_7d, "
    "rec_run_date, forecast_a_7d, forecast_b_7d, recommended_qty_a, recommended_qty_b, risk_type, "
    "lost_revenue_idr, reason_text"
)
_MAX_LIST = 10


def _sku_evidence(row: dict) -> dict:
    keep = ("store_id", "sku", "name", "on_hand", "sold_7d", "stockout_days_7d", "unmet_signals_7d",
            "est_unmet_units_7d", "forecast_a_7d", "forecast_b_7d", "recommended_qty_a", "recommended_qty_b",
            "risk_type", "lost_revenue_idr")
    return {"type": "sku", **{k: row[k] for k in keep if row.get(k) is not None}}


def get_recommendations(store_id: str, risk: str = "", limit: int = 10) -> dict:
    """Reorder recommendations for a store: what to order and why, comparing forecast A and forecast B.

    Forecast A uses POS sales only (it cannot see demand that was lost while a shelf was empty). Forecast B
    adds unmet demand captured from shopper conversations. `recommended_qty_b` > `recommended_qty_a` means
    POS-only ordering would under-order. If the forecast pipeline has not produced recommendations yet,
    `status` is "forecast_not_ready" and `observed_risk` lists SKUs that are empty or have unmet demand
    (observed facts, not forecasts): say clearly that forecasts are not available.

    Args:
        store_id: Store code, e.g. "S01".
        risk: Optional risk_type filter; leave empty for all.
        limit: Maximum number of SKUs (default 10, max 10).

    Returns:
        {status: "ok" | "forecast_not_ready", items | observed_risk: [...], evidence: [...]}
    """
    n = max(1, min(int(limit), _MAX_LIST))
    runner = get_runner()
    rows = runner.rows(f"SELECT {_SUMMARY_COLS} FROM {runner.fq}.v_sku_summary WHERE store_id = @store_id",
                       {"store_id": store_id})
    recs = [r for r in rows if r.get("risk_type") is not None]
    if risk:
        recs = [r for r in recs if r["risk_type"] == risk]
    if recs:
        recs.sort(key=lambda r: (-(r.get("lost_revenue_idr") or 0), r["sku"]))
        items = recs[:n]
        return {"status": "ok", "store_id": store_id, "items": items, "evidence": [_sku_evidence(r) for r in items]}
    observed = [r for r in rows if r.get("is_stockout_today") or (r.get("stockout_days_7d") or 0) > 0
                or (r.get("unmet_signals_7d") or 0) > 0]
    observed.sort(key=lambda r: (-(r.get("est_unmet_units_7d") or 0), -(r.get("stockout_days_7d") or 0), r["sku"]))
    items = [{k: r[k] for k in ("sku", "name", "on_hand", "is_stockout_today", "sold_7d", "stockout_days_7d",
                                "unmet_signals_7d", "est_unmet_units_7d", "price_idr")} for r in observed[:n]]
    return {
        "status": "forecast_not_ready", "store_id": store_id, "observed_risk": items,
        "note": "No forecast-based recommendations exist yet; the list shows observed stockouts and unmet demand.",
        "evidence": [_sku_evidence(r) for r in observed[:n]],
    }


def _resolve_sku(runner, store_id: str, sku: str) -> tuple[str | None, list[dict]]:
    """Accept a SKU code, (part of) a product name, or a category ("coconut milk").

    Returns (sku, []) when exactly one product matches, else (None, candidates) with the candidates that
    have the most unmet demand first, so the caller can pick the one that matters.
    """
    fq = runner.fq
    exact = runner.rows(f"SELECT sku, name FROM {fq}.v_sku_summary WHERE store_id = @s AND sku = @k",
                        {"s": store_id, "k": sku.strip().upper()})
    if exact:
        return exact[0]["sku"], []
    like = runner.rows(
        f"SELECT sku, name, on_hand, est_unmet_units_7d, stockout_days_7d FROM {fq}.v_sku_summary "
        f"WHERE store_id = @s AND (LOWER(name) LIKE @q OR REPLACE(category, '_', ' ') LIKE @q) "
        f"ORDER BY est_unmet_units_7d DESC, sku LIMIT 5", {"s": store_id, "q": f"%{sku.strip().lower()}%"})
    return (like[0]["sku"], []) if len(like) == 1 else (None, like)


def get_sku_detail(store_id: str, sku: str) -> dict:
    """Everything about one product in one store: stock, sales, stockout days, unmet demand, forecast A vs B,
    last 14 days of sales/stock, the latest shopper requests, and any forecast series.

    Args:
        store_id: Store code, e.g. "S01".
        sku: SKU code (e.g. "SNT-001"), a product name or part of it (names are in Bahasa Indonesia, e.g.
            "santan kotak 65"), or a category (e.g. "coconut milk"). When several products match, `status` is
            "ambiguous" and `candidates` lists them, most unmet demand first: pick one and call again.

    Returns:
        {status: "ok" | "not_found" | "ambiguous", summary, daily, recent_requests, forecasts, evidence}
    """
    runner = get_runner()
    code, candidates = _resolve_sku(runner, store_id, sku)
    if code is None:
        return {"status": "ambiguous" if candidates else "not_found", "query": sku, "candidates": candidates}
    p = {"s": store_id, "k": code}
    fq = runner.fq
    jobs = {
        "summary": (f"SELECT {_SUMMARY_COLS} FROM {fq}.v_sku_summary WHERE store_id = @s AND sku = @k", p),
        "daily": (f"SELECT date, qty_sold, closing_stock, is_stockout, unmet_signals, est_unmet_units "
                  f"FROM {fq}.v_unmet_daily WHERE store_id = @s AND sku = @k ORDER BY date DESC LIMIT 14", p),
        "quotes": (f"SELECT date, ts, outcome, requested_text, conversation_id, channel FROM {fq}.v_evidence "
                   f"WHERE store_id = @s AND sku = @k AND outcome IN ('out_of_stock', 'substituted') "
                   f"ORDER BY ts DESC LIMIT 5", p),
        "forecasts": (f"SELECT model, forecast_date, forecast_qty, lower, upper FROM {fq}.forecasts "
                      f"WHERE store_id = @s AND sku = @k AND run_date = "
                      f"(SELECT MAX(run_date) FROM {fq}.forecasts WHERE store_id = @s AND sku = @k) "
                      f"ORDER BY model, forecast_date", p),
    }
    with ThreadPoolExecutor(max_workers=4) as pool:  # four small independent queries
        futures = {k: pool.submit(runner.rows, sql, params) for k, (sql, params) in jobs.items()}
        out = {k: f.result() for k, f in futures.items()}
    summary = out["summary"][0] if out["summary"] else {}
    evidence = [_sku_evidence(summary)] if summary else []
    for q in out["quotes"]:
        evidence.append({"type": "signal", "store_id": store_id, "sku": code, "date": q["date"],
                         "quote": q["requested_text"], "outcome": q["outcome"],
                         "conversation_id": q["conversation_id"]})
    return {
        "status": "ok", "store_id": store_id, "sku": code, "summary": summary, "daily": out["daily"],
        "recent_requests": out["quotes"], "forecasts": out["forecasts"],
        "forecast_available": bool(out["forecasts"]), "evidence": evidence,
    }


def get_lost_revenue(store_id: str = "", days_ago: int = 0) -> dict:
    """Estimated revenue lost to stockouts on one day: unmet shopper demand x price.

    "Today" is the latest day in the data. Use days_ago=1 for yesterday. The estimate is unmet signals divided
    by the share of shoppers who ask the kiosk, times the shelf price.

    Args:
        store_id: Store code, or empty for all stores.
        days_ago: 0 = latest day in the data, 1 = the day before, ...

    Returns:
        {status, date, total_lost_revenue_idr, total_unmet_units, top_items: [...], evidence: [...]}
    """
    runner = get_runner()
    fq = runner.fq
    where = "AND u.store_id = @store_id" if store_id else ""
    params = {"n": max(0, int(days_ago))}
    if store_id:
        params["store_id"] = store_id
    rows = runner.rows(
        f"WITH d AS (SELECT DATE_SUB(MAX(date), INTERVAL @n DAY) AS d FROM {fq}.v_unmet_daily) "
        f"SELECT u.date, u.store_id, u.sku, u.name, u.is_stockout, u.unmet_signals, u.est_unmet_units, "
        f"pm.price_idr, CAST(ROUND(u.est_unmet_units * pm.price_idr) AS INT64) AS est_lost_revenue_idr "
        f"FROM {fq}.v_unmet_daily u JOIN {fq}.product_master pm USING (sku) CROSS JOIN d "
        f"WHERE u.date = d.d AND u.unmet_signals > 0 {where} ORDER BY est_lost_revenue_idr DESC", params)
    if not rows:
        return {"status": "no_data", "store_id": store_id or "all", "days_ago": days_ago,
                "total_lost_revenue_idr": 0, "total_unmet_units": 0, "top_items": [], "evidence": []}
    top = rows[:5]
    return {
        "status": "ok", "store_id": store_id or "all", "date": rows[0]["date"],
        "total_lost_revenue_idr": sum(r["est_lost_revenue_idr"] or 0 for r in rows),
        "total_unmet_units": round(sum(r["est_unmet_units"] or 0 for r in rows), 1),
        "items_affected": len(rows), "top_items": top,
        "evidence": [{"type": "sku", **{k: r[k] for k in ("store_id", "sku", "name", "date", "unmet_signals",
                                                           "est_unmet_units", "est_lost_revenue_idr")}}
                     for r in top],
    }
