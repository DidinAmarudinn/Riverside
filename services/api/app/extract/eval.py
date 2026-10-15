"""Extraction accuracy vs. conversation ground truth (build plan §6.7).

    # from services/api, with PYTHONPATH=.:../../data
    python -m app.extract.eval

Compares data/out/demand_signals.csv against conversations.gt_sku / gt_outcome and reports outcome
accuracy + confusion matrix, two-level SKU accuracy (exact and item+size, ignoring brand — CLAUDE.md
note 4), not_carried recall/precision, confidence spread vs the 0.7 threshold, and failure examples.
Writes docs/extraction-eval.md. Exits 1 if any metric is below the Definition-of-Done threshold.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from .catalog import normalize_name

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = REPO_ROOT / "data" / "out"
DEFAULT_MASTER = REPO_ROOT / "data" / "product_master.csv"
DEFAULT_REPORT = REPO_ROOT / "docs" / "extraction-eval.md"

OUTCOMES = ["out_of_stock", "substituted", "purchased", "not_carried"]
THRESHOLDS = dict(outcome=0.90, sku_exact=0.60, item_size=0.80, nc_recall=0.90)


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bar(x: float, n: int = 28) -> str:
    k = int(round(x * n))
    return "█" * k + "·" * (n - k)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=str(DEFAULT_OUT))
    ap.add_argument("--master", default=str(DEFAULT_MASTER))
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    ap.add_argument("--min-outcome", type=float, default=THRESHOLDS["outcome"])
    ap.add_argument("--min-sku-exact", type=float, default=THRESHOLDS["sku_exact"])
    ap.add_argument("--min-item-size", type=float, default=THRESHOLDS["item_size"])
    ap.add_argument("--min-nc-recall", type=float, default=THRESHOLDS["nc_recall"])
    args = ap.parse_args()

    src = Path(args.src)
    signals = {s["conversation_id"]: s for s in _read_csv(src / "demand_signals.csv")}
    convs = {c["conversation_id"]: c for c in _read_csv(src / "conversations.csv") if c["gt_outcome"]}
    prod = {p["sku"]: p for p in _read_csv(Path(args.master))}
    carried = {sku for sku, p in prod.items() if str(p["is_carried"]).lower() == "true"}
    norm_of = {sku: normalize_name(p["name"], p.get("brand", "")) for sku, p in prod.items()}

    model_version = next(iter(signals.values()))["model_version"] if signals else "?"
    n = len(convs)
    missing = [cid for cid in convs if cid not in signals]

    # ---- outcome ----
    conf = defaultdict(int)
    outcome_ok = below = 0
    for cid, c in convs.items():
        s = signals.get(cid)
        if not s:
            continue
        conf[(c["gt_outcome"], s["outcome"])] += 1
        outcome_ok += c["gt_outcome"] == s["outcome"]
        below += float(s.get("confidence") or 0) < 0.7
    outcome_acc = outcome_ok / n if n else 0.0

    # ---- SKU (only conversations whose gt is a carried SKU) ----
    sku_total = sku_exact = item_size = 0
    sku_fails = []
    for cid, c in convs.items():
        if c["gt_outcome"] == "not_carried" or c["gt_sku"] not in carried:
            continue
        s = signals.get(cid)
        if not s:
            continue
        sku_total += 1
        exact = s.get("sku") == c["gt_sku"]
        gt_norm = norm_of.get(c["gt_sku"], "")
        pred_norm = (s.get("normalized_name") or "").lower()
        same_item = exact or pred_norm == gt_norm or norm_of.get(s.get("sku"), "~") == gt_norm
        sku_exact += exact
        item_size += same_item
        if not same_item and len(sku_fails) < 12:
            sku_fails.append((cid, c["gt_sku"], gt_norm, s.get("sku"), pred_norm))
    sku_exact_acc = sku_exact / sku_total if sku_total else 0.0
    item_size_acc = item_size / sku_total if sku_total else 0.0

    # ---- not_carried ----
    nc_gt = [cid for cid, c in convs.items() if c["gt_outcome"] == "not_carried"]
    nc_hit = sum(1 for cid in nc_gt if signals.get(cid, {}).get("outcome") == "not_carried")
    nc_recall = nc_hit / len(nc_gt) if nc_gt else 0.0
    nc_pred = [cid for cid, s in signals.items() if s["outcome"] == "not_carried"]
    nc_precision = (sum(1 for cid in nc_pred if convs.get(cid, {}).get("gt_outcome") == "not_carried")
                    / len(nc_pred) if nc_pred else 0.0)

    # ---- substitution coverage ----
    sub_gt = [cid for cid, c in convs.items() if c["gt_outcome"] == "substituted"]
    sub_recall = (sum(1 for cid in sub_gt if signals.get(cid, {}).get("outcome") == "substituted")
                  / len(sub_gt) if sub_gt else 0.0)

    out_fails = []
    for cid, c in convs.items():
        s = signals.get(cid)
        if s and s["outcome"] != c["gt_outcome"] and len(out_fails) < 12:
            out_fails.append((cid, c["gt_outcome"], s["outcome"], c["transcript"]))

    # ---- render ----
    L: list[str] = []
    P = lambda *x: L.append(" ".join(str(t) for t in x))  # noqa: E731
    P(f"# Extraction accuracy — {model_version}\n")
    P("All data is synthetic; accuracy is measured against the simulator's hidden ground truth.\n")
    P(f"- Conversations evaluated : **{n}**  (not extracted: {len(missing)})")
    P(f"- Outcome accuracy        : **{outcome_acc:.2%}**  `{_bar(outcome_acc)}`")
    P(f"- SKU exact               : **{sku_exact_acc:.2%}**  `{_bar(sku_exact_acc)}`  (of {sku_total} SKU requests)")
    P(f"- Item + size             : **{item_size_acc:.2%}**  `{_bar(item_size_acc)}`  (brand-insensitive)")
    P(f"- not_carried recall      : **{nc_recall:.2%}**  precision {nc_precision:.2%}  (of {len(nc_gt)})")
    P(f"- substituted recall      : **{sub_recall:.2%}**  (of {len(sub_gt)})")
    P(f"- confidence < 0.7        : {below}  ({below / n:.1%} of evaluated) — excluded from forecast B\n")

    P("## Outcome confusion matrix (row = ground truth, col = prediction)\n")
    P("| gt \\ pred | " + " | ".join(OUTCOMES) + " | total |")
    P("|" + "---|" * (len(OUTCOMES) + 2))
    for gt in OUTCOMES:
        row = [conf.get((gt, pr), 0) for pr in OUTCOMES]
        P(f"| **{gt}** | " + " | ".join(str(v) for v in row) + f" | {sum(row)} |")

    P("\n## Outcome failures (sample)\n")
    for cid, gt, pr, tr in out_fails or []:
        P(f"- `{cid}` gt=**{gt}** pred=**{pr}** — {tr[:160]}")
    if not out_fails:
        P("- (none)")

    P("\n## SKU failures (item+size mismatch, sample)\n")
    for cid, gs, gn, ps, pn in sku_fails or []:
        P(f"- `{cid}` gt=`{gs}` ({gn}) pred=`{ps}` ({pn})")
    if not sku_fails:
        P("- (none)")

    Path(args.report).write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---- console summary + DoD gate ----
    print("\n".join(L))
    checks = [
        ("outcome accuracy", outcome_acc, args.min_outcome),
        ("SKU exact", sku_exact_acc, args.min_sku_exact),
        ("item+size", item_size_acc, args.min_item_size),
        ("not_carried recall", nc_recall, args.min_nc_recall),
    ]
    print("\nDefinition of Done (Langkah 4 accuracy):")
    ok = True
    for name, val, thr in checks:
        passed = val >= thr
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name:<22} {val:.2%} (threshold {thr:.0%})")
    print(f"\nReport: {args.report}")
    if not ok:
        raise SystemExit(1)
    print("Langkah 4 (batch accuracy) passed.")


if __name__ == "__main__":
    main()
