"""Data behind the manager GET routes (docs/api-contract.md §3 and §3.1), camelCase.

Everything here is read from BigQuery with the API's own identity: the contract views for unmet demand,
evidence, gaps and recommendations, and `stock_events` / `pos_sales` for daily series. It never reads
`true_demand` or `gt_*` columns. While the forecast pipeline has not filled `recommendations`, the
recommendation lists are empty and SKU detail reports observed facts only (zero quantities, an explanatory
reasonText); no forecast number is ever invented.
"""
from __future__ import annotations

import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from .tools.bq import get_runner
from .tools.gaps import fetch_gaps

RISK_TYPES = ("stockout_risk", "overstock", "reorder", "unmet_spike")
SERIES_DAYS = 90
EVIDENCE_LIMIT = 20
GAP_LIMIT = 50


class NotFound(LookupError):
    """The store or SKU does not exist (mapped to HTTP 404 by the API layer)."""


def _n(value, default=0):
    return default if value is None else value


def recommendation(row: dict) -> dict:
    """v_sku_summary row -> Recommendation (§3.1)."""
    return {
        "storeId": row["store_id"], "sku": row["sku"], "name": row.get("name") or "",
        "category": row.get("category") or "", "onHand": _n(row.get("on_hand")),
        "forecastA7d": _n(row.get("forecast_a_7d")), "forecastB7d": _n(row.get("forecast_b_7d")),
        "unmet7d": _n(row.get("unmet_7d")), "recommendedQtyA": _n(row.get("recommended_qty_a")),
        "recommendedQtyB": _n(row.get("recommended_qty_b")), "riskType": row["risk_type"],
        "lostRevenueIdr": _n(row.get("lost_revenue_idr")), "reasonText": row.get("reason_text") or "",
    }


def _recommendation_rows(store_id: str, risk: str | None = None) -> list[dict]:
    runner = get_runner()
    rows = runner.rows(f"SELECT * FROM {runner.fq}.v_sku_summary WHERE store_id = @store_id", {"store_id": store_id})
    rows = [r for r in rows if r.get("risk_type")]
    if risk:
        rows = [r for r in rows if r["risk_type"] == risk]
    rows.sort(key=lambda r: (-_n(r.get("lost_revenue_idr")), -_n(r.get("unmet_7d")), r["sku"]))
    return rows


def recommendations(store_id: str, risk: str | None = None) -> dict:
    return {"storeId": store_id, "items": [recommendation(r) for r in _recommendation_rows(store_id, risk)]}


def overview(store_id: str) -> dict:
    runner = get_runner()
    fq = runner.fq
    kpi = runner.rows(
        f"SELECT "
        f"(SELECT COALESCE(SUM(lost_revenue_idr), 0) FROM {fq}.v_lost_revenue_today WHERE store_id = @s) AS lost, "
        f"(SELECT COALESCE(SUM(unmet_qty), 0) FROM {fq}.v_unmet_daily WHERE store_id = @s AND outcome = 'out_of_stock' "
        f" AND date = (SELECT MAX(date) FROM {fq}.demand_signals WHERE sandbox_id IS NULL)) AS unmet, "
        f"(SELECT COUNTIF(is_stockout) FROM {fq}.stock_events WHERE store_id = @s "
        f" AND date = (SELECT MAX(date) FROM {fq}.stock_events)) AS stockouts", {"s": store_id})[0]
    return {
        "storeId": store_id,
        "kpis": {"lostRevenueToday": kpi["lost"], "unmetToday": kpi["unmet"], "stockoutSkus": kpi["stockouts"]},
        "topRisks": [recommendation(r) for r in _recommendation_rows(store_id)[:5]],
    }


def _derived_risk(on_hand: int | None, unmet_7d: int) -> str:
    """Only used while no recommendation exists: classify from observed facts."""
    if on_hand == 0:
        return "stockout_risk"
    return "unmet_spike" if unmet_7d > 0 else "reorder"


def sku_detail(store_id: str, sku: str) -> dict:
    runner = get_runner()
    fq = runner.fq
    p = {"s": store_id, "k": sku}
    jobs = {
        "product": (f"SELECT name, brand, category, pack_size, price_idr, aisle FROM {fq}.product_master WHERE sku = @k",
                    {"k": sku}),
        "days": (f"SELECT e.date, COALESCE(s.qty_sold, 0) AS qty_sold, e.closing_stock, e.is_stockout, "
                 f"COALESCE(u.unmet_qty, 0) AS unmet FROM {fq}.stock_events e "
                 f"LEFT JOIN {fq}.pos_sales s USING (date, store_id, sku) "
                 f"LEFT JOIN {fq}.v_unmet_daily u ON u.date = e.date AND u.store_id = e.store_id AND u.sku = e.sku "
                 f"AND u.outcome = 'out_of_stock' WHERE e.store_id = @s AND e.sku = @k "
                 f"ORDER BY e.date DESC LIMIT {SERIES_DAYS}", p),
        "rec": (f"SELECT * FROM {fq}.v_sku_summary WHERE store_id = @s AND sku = @k", p),
        "forecasts": (f"SELECT model, forecast_date AS date, forecast_qty AS qty, lower, upper FROM {fq}.forecasts "
                      f"WHERE store_id = @s AND sku = @k AND run_date = "
                      f"(SELECT MAX(run_date) FROM {fq}.forecasts WHERE store_id = @s AND sku = @k) "
                      f"ORDER BY forecast_date", p),
        "evidence": (f"SELECT conversation_id, ts, channel, requested_text, outcome, confidence FROM {fq}.v_evidence "
                     f"WHERE store_id = @s AND sku = @k AND outcome IN ('out_of_stock', 'substituted') "
                     f"ORDER BY ts DESC LIMIT {EVIDENCE_LIMIT}", p),
        "evidence_total": (f"SELECT COUNT(*) AS n FROM {fq}.v_evidence WHERE store_id = @s AND sku = @k "
                           f"AND outcome IN ('out_of_stock', 'substituted')", p),
    }
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {k: pool.submit(runner.rows, sql, params) for k, (sql, params) in jobs.items()}
        out = {k: f.result() for k, f in futures.items()}
    if not out["product"] or not out["days"]:
        raise NotFound(f"no data for {store_id}/{sku}")
    prod, days = out["product"][0], list(reversed(out["days"]))  # oldest first
    latest = days[-1]
    last7 = days[-7:]
    unmet_7d = sum(d["unmet"] for d in last7)
    streak = 0
    for d in reversed(days):
        if not d["is_stockout"]:
            break
        streak += 1
    rec = out["rec"][0] if out["rec"] else None
    risk = rec["risk_type"] if rec and rec.get("risk_type") in RISK_TYPES else _derived_risk(
        latest["closing_stock"], unmet_7d)
    forecasts = {"A": [], "B": []}
    for f in out["forecasts"]:
        if f["model"] in forecasts:
            forecasts[f["model"]].append({k: f[k] for k in ("date", "qty", "lower", "upper")})
    return {
        "storeId": store_id, "sku": sku,
        "product": {"name": prod["name"], "brand": prod.get("brand") or "", "category": prod.get("category") or "",
                    "packSize": prod.get("pack_size") or "", "priceIdr": prod["price_idr"],
                    "aisle": prod.get("aisle") or ""},
        "riskType": risk,
        "kpis": {
            "onHand": latest["closing_stock"],
            "lostRevenueIdr": rec["lost_revenue_idr"] if rec and rec.get("lost_revenue_idr") is not None
            else unmet_7d * prod["price_idr"],
            "lostRevenueUnits": unmet_7d, "unmetRequests": unmet_7d, "stockoutDays": streak,
            **({"stockoutSince": days[-streak]["date"]} if streak else {}),
        },
        "sales": [{"date": d["date"], "qty": d["qty_sold"], "isStockout": bool(d["is_stockout"])} for d in days],
        "forecastA": forecasts["A"], "forecastB": forecasts["B"],
        "unmetDaily": [{"date": d["date"], "count": d["unmet"]} for d in days if d["unmet"]],
        "evidence": {
            "total": out["evidence_total"][0]["n"],
            "items": [{"id": e["conversation_id"], "ts": e["ts"].replace(" ", "T") if isinstance(e["ts"], str) else e["ts"],
                       "channel": e["channel"], "quote": e["requested_text"], "outcome": e["outcome"],
                       "confidence": e["confidence"]} for e in out["evidence"]],
        },
        "reason": {
            "recommendedQtyA": _n(rec.get("recommended_qty_a")) if rec else 0,
            "recommendedQtyB": _n(rec.get("recommended_qty_b")) if rec else 0,
            "reasonText": (rec.get("reason_text") or "") if rec else
            "No forecast-based recommendation yet; figures above are observed stock, sales and unmet requests.",
        },
    }


def gaps(store_id: str) -> dict:
    runner = get_runner()
    fq = runner.fq
    items = fetch_gaps(runner, store_id, GAP_LIMIT)
    names = [it["normalized_name"] for it in items]
    series: dict[str, list[int]] = {n: [0] * 14 for n in names}
    if names:
        rows = runner.rows(
            f"WITH d AS (SELECT MAX(date) AS d FROM {fq}.demand_signals WHERE sandbox_id IS NULL) "
            f"SELECT s.normalized_name, DATE_DIFF(d.d, s.date, DAY) AS ago, COUNT(*) AS c "
            f"FROM {fq}.demand_signals s, d WHERE s.sandbox_id IS NULL AND s.outcome = 'not_carried' "
            f"AND s.store_id = @s AND s.date > DATE_SUB(d.d, INTERVAL 14 DAY) GROUP BY 1, 2", {"s": store_id})
        for r in rows:
            if r["normalized_name"] in series and 0 <= r["ago"] < 14:
                series[r["normalized_name"]][13 - r["ago"]] = r["c"]  # oldest first
    price = {r["category"]: r["m"] for r in runner.rows(
        f"SELECT category, CAST(APPROX_QUANTILES(price_idr, 2)[OFFSET(1)] AS INT64) AS m "
        f"FROM {fq}.product_master WHERE is_carried GROUP BY category", {})}
    out = []
    for it in items:
        daily = series[it["normalized_name"]]
        last7, prev7 = sum(daily[7:]), sum(daily[:7])
        trend = round((last7 - prev7) / prev7 * 100) if prev7 else (100 if last7 else 0)
        cat = it.get("category") or ""
        item = {"name": it["normalized_name"], "category": cat or "Other", "requests": it["requests"],
                "firstSeen": it["first_seen"], "lastSeen": it["last_seen"], "daily": daily, "trend7dPct": trend}
        if it["sample_requests"]:
            item["quote"] = it["sample_requests"][0]
        if cat in price:
            item["estRevenueIdr"] = it["requests"] * price[cat]  # requests x typical price of the category
        out.append(item)
    return {"storeId": store_id, "items": out}
