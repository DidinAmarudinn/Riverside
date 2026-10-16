from app.forecast import sync_firestore as sf
from app.tools.bq import set_runner

from .fake_bq import RECS, FakeRunner


class Doc:
    def __init__(self, db, path): self.db, self.path, self.id = db, path, path[1]


class Fake:
    """Just enough Firestore: collections of documents, batches, list_documents."""

    def __init__(self, existing=None):
        self.data = {}
        for coll, ids in (existing or {}).items():
            for i in ids:
                self.data[(coll, i)] = {"old": True}
        self.commits = 0

    def collection(self, name):
        db = self

        class C:
            def document(self, i): return Doc(db, (name, i))
            def list_documents(self): return [Doc(db, k) for k in list(db.data) if k[0] == name]
        return C()

    def batch(self):
        db = self

        class B:
            def __init__(self): self.ops = []
            def set(self, ref, doc): self.ops.append(("set", ref, doc))
            def delete(self, ref): self.ops.append(("delete", ref, None))
            def commit(self):
                db.commits += 1
                for op, ref, doc in self.ops:
                    if op == "set":
                        db.data[ref.path] = doc
                    else:
                        db.data.pop(ref.path, None)
        return B()


def test_build_uses_the_same_documents_as_the_api():
    set_runner(FakeRunner(recs=RECS))
    recs, metrics = sf.build(["S01"])
    assert set(recs) == {"S01_SKU-0001", "S01_SKU-0007"}
    d = recs["S01_SKU-0001"]
    assert d["recommendedQtyB"] == 60 and d["recommendedQtyA"] == 40 and d["riskType"] == "stockout_risk"
    assert {"storeId", "sku", "forecastA7d", "forecastB7d", "unmet7d", "lostRevenueIdr", "reasonText"} <= d.keys()
    assert metrics["S01"] == {"lostRevenueToday": 9000, "unmetToday": 2, "stockoutSkus": 1}


def test_sync_writes_by_id_and_is_idempotent():
    set_runner(FakeRunner(recs=RECS))
    recs, metrics = sf.build(["S01"])
    db = Fake()
    assert sf.sync(db, recs, metrics) == {"recommendations_written": 2, "metrics_written": 1, "recommendations_pruned": 0}
    first = dict(db.data)
    sf.sync(db, recs, metrics)
    assert db.data == first and ("metrics", "S01") in db.data and ("recommendations", "S01_SKU-0001") in db.data


def test_dry_run_writes_nothing_and_prune_removes_only_stale_base_documents():
    set_runner(FakeRunner(recs=RECS))
    recs, metrics = sf.build(["S01"])
    db = Fake(existing={"recommendations": ["S01_OLD"], "sandboxes": ["abc"]})
    counts = sf.sync(db, recs, metrics, prune=True, dry_run=True)
    assert counts["recommendations_pruned"] == 1 and db.commits == 0 and ("recommendations", "S01_SKU-0001") not in db.data
    sf.sync(db, recs, metrics, prune=True)
    assert ("recommendations", "S01_OLD") not in db.data           # stale base document gone
    assert ("sandboxes", "abc") in db.data                          # visitor data is never touched


def test_large_syncs_are_split_into_batches():
    db = Fake()
    recs = {f"S01_{i}": {"storeId": "S01", "sku": str(i)} for i in range(900)}
    sf.sync(db, recs, {})
    assert db.commits == 3 and len(db.data) == 900
