import uuid

from fastapi.testclient import TestClient

from app import main
from app.demo.sandbox import SCENARIO, reset_sandbox


class FakeBox:
    def __init__(self, subs, exists):
        self.subs, self.exists, self.written = subs, exists, None

    def collections(self):
        return iter(self.subs)

    def get(self):
        return self

    def set(self, data, merge=False):
        self.written = (data, merge)


class FakeDb:
    def __init__(self, box):
        self.box, self.deleted, self.path = box, [], []

    def collection(self, name):
        self.path.append(name)
        return self

    def document(self, doc_id):
        self.path.append(doc_id)
        return self.box

    def recursive_delete(self, ref):
        self.deleted.append(ref)
        return 3


def test_reset_deletes_every_subcollection_and_stamps_the_doc():
    box = FakeBox(["liveSignals", "metrics", "alerts", "sessions"], exists=True)
    db = FakeDb(box)
    assert reset_sandbox("box-1", db) == 12
    assert db.path == ["sandboxes", "box-1"]
    assert db.deleted == ["liveSignals", "metrics", "alerts", "sessions"]
    data, merge = box.written
    assert merge and data["scenario"] == SCENARIO and "lastResetAt" in data and "createdAt" not in data


def test_reset_of_a_new_sandbox_sets_created_at():
    box = FakeBox([], exists=False)
    assert reset_sandbox("box-2", FakeDb(box)) == 0
    assert "createdAt" in box.written[0]


def test_reset_endpoint_drops_only_this_sandboxs_kiosk_sessions():
    client = TestClient(main.app)
    mine, other = str(uuid.uuid4()), str(uuid.uuid4())
    sessions = {}
    for box in (mine, other):
        r = client.post("/api/kiosk/sessions", json={"storeId": "S01"}, headers={"X-Sandbox-Id": box})
        sessions[box] = r.json()["sessionId"]
    assert client.post("/api/demo/reset", headers={"X-Sandbox-Id": mine}).status_code == 204
    assert sessions[mine] not in main._kiosk_sessions
    assert sessions[other] in main._kiosk_sessions
