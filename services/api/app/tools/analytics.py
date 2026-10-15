"""Manager-agent tools over the Demand Radar dataset (all queries parametrised, read-only).

Views (contract docs/api-contract.md §1) hold unmet demand, evidence, gaps and the latest recommendations. Daily
stock and sales are not in the views, so the tools read `stock_events` / `pos_sales` with the API's own identity
(never `true_demand` or any `gt_*` column). Every tool returns `evidence` items; the agent callback numbers them
E1, E2, ... and the model cites them.

"Unmet" figures are *observed* shopper requests that could not be served (out_of_stock). Only the share of
shoppers who talk to the kiosk is observed, so real lost demand is higher.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .bq import get_runner

_MAX_LIST = 10
_AS_OF = "(SELECT MAX(date) FROM {fq}.stock_events)"


def _sku_evidence(row: dict) -> dict:
    keep = ("store_id", "sku", "name", "on_hand", "stockout_days_7d", "unmet_requests_7d", "unmet_7d",
            "forecast_a_7d", "forecast_b_7d", "recommended_qty_a", "recommended_qty_b", "risk_type",
            "lost_revenue_idr")
    return {"type": "sku", **{k: row[k] for k in keep if row.get(k) is not None}}


def get_recommendations(store_id: str, risk: str = "", limit: int = 10) -> dict:
    """Reorder recommendations for a store: what to order and why, comparing forecast A and forecast B.

    Forecast A uses POS sales only (it cannot see demand that was lost while a shelf was empty). Forecast B
    adds unmet demand captured from shopper conversations. `recommended_qty_b` > `recommended_qty_a` means
    POS-only ordering would under-order. If the forecast pipeline has not produced recommendations yet,
    `status` is "forecast_not_ready" and `observed_risk` lists SKUs that are empty or had unmet requests in the
    last 7 days (observed facts, not forecasts): say clearly that forecasts are not available.

    Args:
        store_id: Store code, e.g. "S01".
        risk: Optional risk_type filter; leave empty for all.
        limit: Maximum number of SKUs (default 10, max 10).

    Returns:
        {status: "ok" | "forecast_not_ready", items | observed_risk: [...], as_of, evidence: [...]}
    """
    n = max(1, min(int(limit), _MAX_LIST))
    runner = get_runner()
    fq = runner.fq
    recs = runner.rows(f"SELECT * FROM {fq}.v_sku_summary WHERE store_id = @store_id", {"store_id": store_id})
    if risk:
        recs = [r for r in recs if r.get("risk_type") == risk]
    if recs:
        recs.sort(key=lambda r: (-(r.get("lost_revenue_idr") or 0), r["sku"]))
        items = recs[:n]
        return {"status": "ok", "store_id": store_id, "run_date": items[0].get("run_date"), "items": items,
                "evidence": [_sku_evidence(r) for r in items]}
    as_of = _AS_OF.format(fq=fq)
    observed = runner.rows(
        f"WITH d AS (SELECT {as_of} AS d), "
        f"stock AS (SELECT s.sku, s.closing_stock FROM {fq}.stock_events s, d WHERE s.store_id = @store_id AND s.date = d.d), "
        f"out AS (SELECT s.sku, COUNTIF(s.is_stockout) AS stockout_days_7d FROM {fq}.stock_events s, d "
        f"WHERE s.store_id = @store_id AND s.date > DATE_SUB(d.d, INTERVAL 7 DAY) GROUP BY s.sku), "
        f"unmet AS (SELECT u.sku, SUM(u.unmet_qty) AS unmet_requests_7d FROM {fq}.v_unmet_daily u, d "
        f"WHERE u.store_id = @store_id AND u.outcome = 'out_of_stock' AND u.date > DATE_SUB(d.d, INTERVAL 7 DAY) "
        f"GROUP BY u.sku) "
        f"SELECT p.sku, p.name, p.price_idr, st.closing_stock AS on_hand, COALESCE(o.stockout_days_7d, 0) AS stockout_days_7d, "
        f"COALESCE(un.unmet_requests_7d, 0) AS unmet_requests_7d "
        f"FROM {fq}.product_master p JOIN stock st USING (sku) LEFT JOIN out o USING (sku) LEFT JOIN unmet un USING (sku) "
        f"WHERE p.is_carried AND (st.closing_stock = 0 OR COALESCE(o.stockout_days_7d, 0) > 0 OR COALESCE(un.unmet_requests_7d, 0) > 0) "
        f"ORDER BY unmet_requests_7d DESC, stockout_days_7d DESC, p.sku LIMIT @n", {"store_id": store_id, "n": n})
    return {
        "status": "forecast_not_ready", "store_id": store_id, "observed_risk": observed,
        "note": "No forecast-based recommendations exist yet; the list shows observed stockouts and unmet requests.",
        "evidence": [_sku_evidence({"store_id": store_id, **r}) for r in observed],
    }


def _resolve_sku(runner, store_id: str, sku: str) -> tuple[str | None, list[dict]]:
    """Accept a SKU code, (part of) a product name, or one of the catalog's synonyms ("santan", "migor").

    Returns (sku, []) when exactly one product matches, else (None, candidates) with the candidates that have
    the most unmet requests first, so the caller can pick the one that matters.
    """
    fq = runner.fq
    exact = runner.rows(f"SELECT sku, name FROM {fq}.product_master WHERE is_carried AND sku = @k",
                        {"k": sku.strip().upper()})
    if exact:
        return exact[0]["sku"], []
    like = runner.rows(
        f"SELECT p.sku, p.name, COALESCE(SUM(u.unmet_qty), 0) AS unmet_requests_total "
        f"FROM {fq}.product_master p LEFT JOIN {fq}.v_unmet_daily u "
        f"ON u.sku = p.sku AND u.store_id = @s AND u.outcome = 'out_of_stock' "
        f"WHERE p.is_carried AND (LOWER(p.name) LIKE @q OR EXISTS "
        f"(SELECT 1 FROM UNNEST(p.synonyms) y WHERE LOWER(y) LIKE @q)) "
        f"GROUP BY p.sku, p.name ORDER BY unmet_requests_total DESC, p.sku LIMIT 5",
        {"s": store_id, "q": f"%{sku.strip().lower()}%"})
    return (like[0]["sku"], []) if len(like) == 1 else (None, like)


def get_sku_detail(store_id: str, sku: str) -> dict:
    """Everything about one product in one store: product info, stock now, sales and stockout days (7 and 28
    days), unmet requests, the last 14 days day by day, the latest shopper requests, the recommendation with
    forecast A vs B, and any forecast series.

    Args:
        store_id: Store code, e.g. "S01".
        sku: SKU code (e.g. "SKU-0001"), a product name or part of it, or a catalog synonym (names are in Bahasa
            Indonesia: "santan kotak 65", "migor"). When several products match, `status` is "ambiguous" and
            `candidates` lists them, most unmet requests first: pick one and call again.

    Returns:
        {status: "ok" | "not_found" | "ambiguous", product, stock, last_14_days, recommendation, recent_requests,
        forecasts, forecast_available, evidence}
    """
    runner = get_runner()
    code, candidates = _resolve_sku(runner, store_id, sku)
    if code is None:
        return {"status": "ambiguous" if candidates else "not_found", "query": sku, "candidates": candidates}
    p = {"s": store_id, "k": code}
    fq = runner.fq
    jobs = {
        "product": (f"SELECT sku, name, brand, category, pack_size, price_idr, aisle, shelf_life_days "
                    f"FROM {fq}.product_master WHERE sku = @k", {"k": code}),
        "days": (f"SELECT e.date, COALESCE(s.qty_sold, 0) AS qty_sold, e.closing_stock, e.is_stockout, "
                 f"COALESCE(u.unmet_qty, 0) AS unmet_requests "
                 f"FROM {fq}.stock_events e LEFT JOIN {fq}.pos_sales s USING (date, store_id, sku) "
                 f"LEFT JOIN {fq}.v_unmet_daily u ON u.date = e.date AND u.store_id = e.store_id AND u.sku = e.sku "
                 f"AND u.outcome = 'out_of_stock' "
                 f"WHERE e.store_id = @s AND e.sku = @k ORDER BY e.date DESC LIMIT 28", p),
        "recommendation": (f"SELECT * FROM {fq}.v_sku_summary WHERE store_id = @s AND sku = @k", p),
        "quotes": (f"SELECT date, ts, outcome, requested_text, conversation_id, channel FROM {fq}.v_evidence "
                   f"WHERE store_id = @s AND sku = @k AND outcome IN ('out_of_stock', 'substituted') "
                   f"ORDER BY ts DESC LIMIT 5", p),
        "forecasts": (f"SELECT model, forecast_date, forecast_qty, lower, upper FROM {fq}.forecasts "
                      f"WHERE store_id = @s AND sku = @k AND run_date = "
                      f"(SELECT MAX(run_date) FROM {fq}.forecasts WHERE store_id = @s AND sku = @k) "
                      f"ORDER BY model, forecast_date", p),
    }
    with ThreadPoolExecutor(max_workers=5) as pool:  # five small independent queries
        futures = {k: pool.submit(runner.rows, sql, params) for k, (sql, params) in jobs.items()}
        out = {k: f.result() for k, f in futures.items()}
    product = out["product"][0] if out["product"] else {}
    days = out["days"]
    d7, d28 = days[:7], days[:28]
    stock = {
        "as_of": days[0]["date"] if days else None, "on_hand": days[0]["closing_stock"] if days else None,
        "sold_7d": sum(d["qty_sold"] for d in d7), "sold_28d": sum(d["qty_sold"] for d in d28),
        "stockout_days_7d": sum(1 for d in d7 if d["is_stockout"]),
        "stockout_days_28d": sum(1 for d in d28 if d["is_stockout"]),
        "unmet_requests_7d": sum(d["unmet_requests"] for d in d7),
        "unmet_requests_28d": sum(d["unmet_requests"] for d in d28),
    }
    rec = out["recommendation"][0] if out["recommendation"] else None
    evidence = [_sku_evidence({"store_id": store_id, "sku": code, "name": product.get("name"),
                               "on_hand": stock["on_hand"], "stockout_days_7d": stock["stockout_days_7d"],
                               "unmet_requests_7d": stock["unmet_requests_7d"],
                               **({k: rec[k] for k in ("forecast_a_7d", "forecast_b_7d", "recommended_qty_a",
                                                       "recommended_qty_b", "risk_type", "lost_revenue_idr")}
                                  if rec else {})})]
    for q in out["quotes"]:
        evidence.append({"type": "signal", "store_id": store_id, "sku": code, "date": q["date"],
                         "quote": q["requested_text"], "outcome": q["outcome"],
                         "conversation_id": q["conversation_id"]})
    return {
        "status": "ok", "store_id": store_id, "sku": code, "product": product, "stock": stock,
        "last_14_days": days[:14], "recommendation": rec, "recent_requests": out["quotes"],
        "forecasts": out["forecasts"], "forecast_available": bool(out["forecasts"]), "evidence": evidence,
    }


def get_lost_revenue(store_id: str = "", days_ago: int = 0) -> dict:
    """Revenue lost to stockouts on one day: unmet (out_of_stock) shopper requests x shelf price.

    "Today" is the latest day in the data. Use days_ago=1 for yesterday. Only requests actually captured from
    shoppers are counted, so this is a lower bound.

    Args:
        store_id: Store code, or empty for all stores.
        days_ago: 0 = latest day in the data, 1 = the day before, ...

    Returns:
        {status, date, total_lost_revenue_idr, total_unmet_qty, items_affected, top_items: [...], evidence: [...]}
    """
    runner = get_runner()
    fq = runner.fq
    where = "AND u.store_id = @store_id" if store_id else ""
    params: dict = {"n": max(0, int(days_ago))}
    if store_id:
        params["store_id"] = store_id
    rows = runner.rows(
        f"WITH d AS (SELECT DATE_SUB(MAX(date), INTERVAL @n DAY) AS d FROM {fq}.v_signals) "
        f"SELECT u.date, u.store_id, u.sku, p.name, u.unmet_qty, p.price_idr, "
        f"u.unmet_qty * p.price_idr AS lost_revenue_idr "
        f"FROM {fq}.v_unmet_daily u JOIN {fq}.product_master p USING (sku) CROSS JOIN d "
        f"WHERE u.outcome = 'out_of_stock' AND u.date = d.d {where} ORDER BY lost_revenue_idr DESC", params)
    if not rows:
        return {"status": "no_data", "store_id": store_id or "all", "days_ago": days_ago,
                "total_lost_revenue_idr": 0, "total_unmet_qty": 0, "items_affected": 0, "top_items": [],
                "evidence": []}
    top = rows[:5]
    return {
        "status": "ok", "store_id": store_id or "all", "date": rows[0]["date"],
        "total_lost_revenue_idr": sum(r["lost_revenue_idr"] or 0 for r in rows),
        "total_unmet_qty": sum(r["unmet_qty"] or 0 for r in rows),
        "items_affected": len(rows), "top_items": top,
        "evidence": [{"type": "sku", **{k: r[k] for k in ("store_id", "sku", "name", "date", "unmet_qty",
                                                           "lost_revenue_idr")}} for r in top],
    }
