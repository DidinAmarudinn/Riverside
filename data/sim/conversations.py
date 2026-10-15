"""Synthetic shopper conversations (informal Bahasa Indonesia) derived from the simulated world.

Every conversation carries a hidden ground truth (`gt`) so extraction accuracy can be scored.
The text generator is template-based and works offline. If `phrasebank.generated.json`
exists (produced by `sim.gen_phrasebank`, which asks Gemini for extra phrasings) a share of
mentions are drawn from it, which widens the vocabulary beyond the templates.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .catalog import FAMILIES, NOT_STOCKED, nc_sku
from .engine import World

# Ground-truth outcome vocabulary = contract demand_signals.outcome (docs/api-contract.md §1).
OUTCOME_NOT_CARRIED = "not_carried"
OUTCOME_PURCHASED = "purchased"
OUTCOME_OUT_OF_STOCK = "out_of_stock"
OUTCOME_SUBSTITUTED = "substituted"

PHRASEBANK_PATH = Path(__file__).with_name("phrasebank.generated.json")

PREFIXES = ["", "", "", "", "kak ", "min ", "halo ", "pagi kak, ", "permisi kak, ", "sore, ",
            "malam kak ", "hai, ", "mas ", "mba ", "bang "]
SUFFIXES = ["", "", "", "", " kak", " dong", " ya", " yaa", " nih", " deh", " gan", " plis", " cepet ya"]
FRAMES = [
    "ada {x}?", "{x} ada ga?", "{x} ada gak?", "cari {x}", "{x} dimana ya?", "{x} masih ada?",
    "mau beli {x}", "nyari {x} nih", "{x} kosong ya?", "ada {x} ga ya?", "{x} di rak mana?",
    "permisi {x} ada?", "tanya {x} ada ga", "{x} stoknya ada?", "lagi nyari {x}, ada?",
    "mau tanya, {x} ada nggak?", "{x} ready?", "ada jual {x}?", "{x} ada ngga",
]
FOLLOW_FRAMES = ["terus {x} ada juga?", "sama {x} ada ga?", "oh iya {x} juga dong", "satu lagi, {x} ada?"]
CONTEXTS = ["buat masak", "buat sarapan", "buat ikan bakar", "buat anak", "buat diet", "buat arisan"]
DECLINES = ["yah yaudah deh makasih", "oke nanti aja deh", "yaudah ga jadi", "hmm yaudah kak thanks",
            "ok nanti balik lagi", "yah kosong, yaudah"]
ACCEPTS = ["boleh deh yang itu aja", "oke ambil yang itu", "yaudah deh yang itu", "boleh kak, di rak mana?"]
THANKS = ["oke makasih kak", "sip makasih", "makasih ya", "oke thanks"]
NO_DEMAND = [
    ("toilet di mana ya?", "Toilet ada di dekat pintu keluar sebelah kiri, kak."),
    ("jam buka sampai jam berapa?", "Toko buka sampai jam 22.00 setiap hari, kak."),
    ("bisa bayar pake QRIS ga?", "Bisa kak, kami terima QRIS dan kartu debit."),
    ("parkir motor gratis ga?", "Parkir motor gratis untuk 2 jam pertama ya, kak."),
    ("ada promo hari ini?", "Hari ini ada promo buah segar dan tisu di bagian depan, kak."),
]
SIZE_WORDS = {0: "kecil", 1: "sedang", 2: "besar"}


# ----------------------------------------------------------------------------- text helpers

def _typo(word: str, rng: np.random.Generator) -> str:
    if len(word) < 4:
        return word
    i = int(rng.integers(1, len(word) - 1))
    op = int(rng.integers(0, 4))
    if op == 0:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]       # swap
    if op == 1:
        return word[:i] + word[i + 1:]                                 # drop
    if op == 2:
        return word[:i] + word[i] + word[i:]                           # double
    return word[:i] + {"a": "e", "e": "a", "i": "e", "o": "u", "u": "o"}.get(word[i], word[i]) + word[i + 1:]


def _maybe_typo(text: str, rng: np.random.Generator, p: float = 0.25) -> str:
    if rng.random() > p:
        return text
    words = text.split()
    j = int(rng.integers(0, len(words)))
    words[j] = _typo(words[j], rng)
    return " ".join(words)


def _size_natural(label: str, rng: np.random.Generator) -> str:
    n, _, unit = label.partition(" ")
    unit_l = unit.lower()
    if unit_l == "ml":
        return str(rng.choice([f"{n} ml", f"{n}ml"]))
    if unit_l == "l":
        return str(rng.choice([f"{n} liter", f"{n}l", f"{n} L"]))
    if unit_l == "g":
        return str(rng.choice([f"{n} g", f"{n}gr", f"{n} gram"]))
    if unit_l == "kg":
        return str(rng.choice([f"{n} kg", f"{n}kg", f"{n} kilo"]))
    return label.lower()


def _compose(core: str, rng: np.random.Generator, follow: bool = False) -> str:
    frame = str(rng.choice(FOLLOW_FRAMES if follow else FRAMES))
    msg = ("" if follow else str(rng.choice(PREFIXES))) + frame.format(x=core) + str(rng.choice(SUFFIXES))
    if rng.random() < 0.15:
        msg = msg.replace("?", "")
    if rng.random() < 0.3:
        msg = msg[:1].upper() + msg[1:]
    return msg


# ----------------------------------------------------------------------------- catalog lookups

def _sku_meta(master: pd.DataFrame) -> dict[str, dict]:
    """Per-SKU family aliases and size rank (same iteration order as build_product_master)."""
    meta, n = {}, 0
    for fam in FAMILIES:
        for rank, (label, _price, _share) in enumerate(fam.sizes):
            n += 1
            meta[f"SKU-{n:04d}"] = {"aliases": list(fam.aliases) or [fam.product.lower()],
                                    "rank": rank, "n_sizes": len(fam.sizes)}
    assert len(meta) == len(master), "catalog and product_master are out of sync; rebuild product master"
    return meta


def _load_phrasebank() -> dict[str, list[str]]:
    if PHRASEBANK_PATH.exists():
        try:
            return json.loads(PHRASEBANK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


class Phraser:
    def __init__(self, world: World, rng: np.random.Generator):
        self.world, self.rng = world, rng
        self.master = world.master.set_index("sku")
        self.meta = _sku_meta(world.master)
        self.bank = _load_phrasebank()

    def sku_mention(self, sku: str) -> str:
        rng, row, m = self.rng, self.master.loc[sku], self.meta[sku]
        banked = self.bank.get(f"sku:{sku}")
        if banked and rng.random() < 0.35:
            return str(rng.choice(banked))
        product = row["name"].replace(row["pack_size"], "").replace(row["brand"], "").strip().lower()
        brand, size = str(row["brand"]).lower(), row["pack_size"]
        alias = str(rng.choice(m["aliases"]))
        size_nat = _size_natural(size, rng)
        if m["n_sizes"] >= 3:
            size_word = SIZE_WORDS[min(m["rank"], 2)]
        else:
            size_word = "kecil" if m["rank"] == 0 else "besar"
        style = rng.choice(["full", "alias_size", "alias_word", "alias_only", "brand_short", "no_brand"],
                           p=[.28, .22, .18, .08, .12, .12])
        if style == "full":
            text = " ".join(p for p in (product, brand, size_nat) if p)
        elif style == "alias_size":
            text = f"{alias} {size_nat}"
        elif style == "alias_word" and m["n_sizes"] > 1:
            text = f"{alias} {size_word}"
        elif style == "brand_short" and brand:
            text = f"{brand} {alias.replace(brand, '').strip() or product}"
        elif style == "no_brand":
            text = f"{product} {size_nat}"
        else:
            text = alias
        return _maybe_typo(" ".join(text.split()), rng)

    def gap_mention(self, idx: int) -> str:
        rng, item = self.rng, NOT_STOCKED[idx]
        banked = self.bank.get(f"gap:{item.name}")
        text = str(rng.choice(banked)) if banked and rng.random() < 0.35 else str(rng.choice(item.aliases))
        if rng.random() < 0.15:
            text = f"{text} {rng.choice(CONTEXTS)}"
        return _maybe_typo(text, rng, 0.2)


# ----------------------------------------------------------------------------- exchange builders

def _exchange(ph: Phraser, ev: dict, follow: bool) -> tuple[list[dict], dict]:
    """One shopper question + agent reply (+ optional wrap-up). Returns (turns, ground_truth_item)."""
    rng, master = ph.rng, ph.master
    outcome = ev["outcome"]

    if outcome == "not_stocked":
        mention = ph.gap_mention(ev["gap"])
        item = NOT_STOCKED[ev["gap"]]
        turns = [{"role": "shopper", "text": _compose(mention, rng, follow)},
                 {"role": "agent", "text": f"Maaf kak, kami belum menjual {item.aliases[0]}. Permintaannya saya catat ya, "
                                           f"semoga segera kami sediakan."}]
        if rng.random() < .6:
            turns.append({"role": "shopper", "text": str(rng.choice(THANKS + ["yah sayang banget"]))})
        # gt_sku points at the NC-xxx row; the extractor still emits sku=NULL for not_carried.
        return turns, {"sku": nc_sku(ev["gap"]), "requested_item": item.name, "category": item.category,
                       "outcome": OUTCOME_NOT_CARRIED, "qty": 1, "substitute_sku": None}

    sku = ev["sku"]
    row = master.loc[sku]
    mention = ph.sku_mention(sku)
    q = _compose(mention, rng, follow)
    ref = row["name"] if rng.random() < 0.7 else mention          # exact name vs echo of the shopper's phrase
    turns = [{"role": "shopper", "text": q}]

    if outcome == "bought":
        turns.append({"role": "agent", "text": f"Ada kak, {ref} ada di rak {row['aisle']}. "
                                               f"Harganya Rp{int(row['price_idr']):,}.".replace(",", ".")})
        if rng.random() < .5:
            turns.append({"role": "shopper", "text": str(rng.choice(THANKS))})
        gt = {"sku": sku, "requested_item": None, "category": None, "outcome": OUTCOME_PURCHASED,
              "qty": 1, "substitute_sku": None}
        return turns, gt

    alt = ev.get("alt")
    if alt is not None:
        arow = master.loc[alt]
        offer = f" Mau coba {arow['name']}? Ada di rak {arow['aisle']}."
    else:
        offer = " Mau saya catat supaya segera diisi ulang?"
    turns.append({"role": "agent", "text": f"Maaf kak, {ref} lagi kosong nih.{offer}"})
    if outcome == "substituted":
        turns += [{"role": "shopper", "text": str(rng.choice(ACCEPTS))},
                  {"role": "agent", "text": f"Siap kak, {arow['name']} ada di rak {arow['aisle']}."}]
    else:
        turns.append({"role": "shopper", "text": str(rng.choice(DECLINES))})
    gt = {"sku": sku, "requested_item": None, "category": None,
          "outcome": OUTCOME_SUBSTITUTED if outcome == "substituted" else OUTCOME_OUT_OF_STOCK,
          "qty": 1, "substitute_sku": alt if outcome == "substituted" else None}
    return turns, gt


# ----------------------------------------------------------------------------- main generator

HOUR_WEIGHTS = np.array([1, 2, 4, 5, 5, 4, 3, 3, 4, 5, 6, 6, 4, 2], dtype=float)  # hours 08..21
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()


def _alt_candidates(master: pd.DataFrame) -> dict[int, list[int]]:
    """Substitute candidates for each SKU: other SKUs in the same subcategory."""
    sub = master["subcategory"].to_numpy()
    return {k: [j for j in range(len(master)) if j != k and sub[j] == sub[k]] for k in range(len(master))}


def generate_conversations(world: World, seed: int | None = None) -> pd.DataFrame:
    cfg = world.cfg
    conv_cfg = cfg.sim["conversations"]
    rng = np.random.default_rng((seed if seed is not None else int(cfg.sim["seed"])) + 1)
    ph = Phraser(world, rng)
    D, S, K = world.shape
    unmet = world.demand - world.sales
    alts = _alt_candidates(world.master)

    # Scenarios that pin an exact unmet-conversation count (hero): generate those cells
    # deterministically and keep the random sampler from also drawing from them.
    date_strs = list(world.dates.strftime("%Y-%m-%d"))
    store_to_s = {sid: i for i, sid in enumerate(world.store_ids)}
    sku_to_k = {sku: i for i, sku in enumerate(world.skus)}
    hero_cells: set[tuple[int, int]] = set()
    hero_specs: list[tuple[int, int, list[int], int]] = []
    for rs in world.resolved_scenarios:
        n = int(rs.get("unmet_conversations", 0) or 0)
        if n <= 0 or rs.get("sku") not in sku_to_k:
            continue
        s, k = store_to_s[rs["store_id"]], sku_to_k[rs["sku"]]
        days = list(range(date_strs.index(rs["start_date"]), date_strs.index(rs["end_date"]) + 1))
        hero_cells.add((s, k))
        hero_specs.append((s, k, days, n))

    # --- 1. sample events (who talked to the kiosk about what) --------------------------
    n_bought = rng.binomial(world.sales, conv_cfg["p_chat_in_stock"])
    n_unmet = rng.binomial(unmet, conv_cfg["p_chat_unmet"])
    events: list[dict] = []

    for d, s, k in np.argwhere(n_bought > 0):
        for _ in range(n_bought[d, s, k]):
            events.append({"d": d, "s": s, "sku": world.skus[k], "outcome": "bought"})

    for d, s, k in np.argwhere(n_unmet > 0):
        if (s, k) in hero_cells:
            continue                                   # pinned below, don't double-count
        in_stock_alts = [j for j in alts[k] if world.opening[d, s, j] > 0]
        for _ in range(n_unmet[d, s, k]):
            alt = world.skus[int(rng.choice(in_stock_alts))] if in_stock_alts else None
            substituted = alt is not None and rng.random() < conv_cfg["p_substitute"]
            events.append({"d": d, "s": s, "sku": world.skus[k], "alt": alt,
                           "outcome": "substituted" if substituted else "out_of_stock"})

    # Pinned hero unmet: exactly n conversations spread across the stockout window (all declined).
    for s, k, days, n in hero_specs:
        for i in range(n):
            events.append({"d": days[i % len(days)], "s": s, "sku": world.skus[k],
                           "alt": None, "outcome": "out_of_stock"})

    gap_w = np.array([g.weight for g in NOT_STOCKED])
    for sc in cfg.scenarios:
        if sc["type"] == "assortment_gap":
            gap_w[[g.name for g in NOT_STOCKED].index(sc["item"])] *= float(sc["demand_multiplier"])
    gap_w = gap_w / gap_w.sum()
    n_gap = rng.poisson(conv_cfg["not_stocked_per_store_day"], size=(D, S))
    for d, s in np.argwhere(n_gap > 0):
        for g in rng.choice(len(NOT_STOCKED), size=n_gap[d, s], p=gap_w):
            events.append({"d": d, "s": s, "gap": int(g), "outcome": "not_stocked"})

    # --- 2. group into conversations (some multi-item, some chit-chat) -------------------
    rng.shuffle(events)
    by_cell: dict[tuple[int, int], list[dict]] = {}
    for ev in events:
        by_cell.setdefault((ev["d"], ev["s"]), []).append(ev)

    rows = []
    n_conv = 0
    for (d, s), evs in sorted(by_cell.items()):
        i = 0
        while i < len(evs):
            take = 2 if (i + 1 < len(evs) and rng.random() < conv_cfg["multi_item_share"]) else 1
            group, i = evs[i:i + take], i + take
            turns, gts = [], []
            for j, ev in enumerate(group):
                t, gt = _exchange(ph, ev, follow=j > 0)
                turns += t
                gts.append(gt)
            rows.append((d, s, turns, gts))
    n_chit = int(len(rows) * conv_cfg["no_demand_share"])
    for _ in range(n_chit):
        q, a = NO_DEMAND[int(rng.integers(0, len(NO_DEMAND)))]
        rows.append((int(rng.integers(0, D)), int(rng.integers(0, S)),
                     [{"role": "shopper", "text": _maybe_typo(q, rng, .3)}, {"role": "agent", "text": a}], []))

    out = []
    for d, s, turns, gts in rows:
        n_conv += 1
        hour = 8 + int(rng.choice(len(HOUR_WEIGHTS), p=HOUR_WEIGHTS))
        ts = world.dates[d] + pd.Timedelta(hours=hour, minutes=int(rng.integers(0, 60)), seconds=int(rng.integers(0, 60)))
        primary = gts[0] if gts else None               # contract carries scalar gt per conversation
        out.append({
            "conversation_id": f"C{n_conv:06d}",
            "store_id": world.store_ids[s],
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
            "channel": str(rng.choice(["kiosk", "chat"], p=[.7, .3])),
            "transcript": json.dumps(turns, ensure_ascii=False),
            "gt_sku": (primary or {}).get("sku") or "",
            "gt_outcome": (primary or {}).get("outcome") or "",
        })
    df = pd.DataFrame(out).sort_values("ts").reset_index(drop=True)
    df["conversation_id"] = [f"C{i + 1:06d}" for i in range(len(df))]
    return df


def flatten_transcript(transcript: str | list[dict]) -> str:
    turns = json.loads(transcript) if isinstance(transcript, str) else transcript
    return "\n".join(f"{'Shopper' if t['role'] == 'shopper' else 'Agent'}: {t['text']}" for t in turns)
