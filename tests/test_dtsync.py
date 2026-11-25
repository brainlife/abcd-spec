import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtrecord  # noqa: E402
import dtsync  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
REC = dtrecord.load(FIX / "dt-neuro.dwi.json")
LIVE = next(d for d in json.loads((FIX / "dt-api-snapshot.json").read_text())["datatypes"] if d["name"] == "neuro/dwi")


class RecordingHttp:
    def __init__(self, fail_on_put=None, found=0):
        self.puts, self.posts, self.deletes, self.fail_on_put, self.found = [], [], [], fail_on_put, found

    def get(self, path):
        return {"count": self.found, "datasets": [], "apps": []}

    def put(self, path, body):
        self.puts.append((path, body))
        if self.fail_on_put == len(self.puts):
            raise RuntimeError("network down")
        return body

    def post(self, path, body):
        self.posts.append((path, body))
        return dict(body, _id="0" * 24)

    def delete(self, path):
        self.deletes.append(path)


def _change(name, _id):
    return {"name": name, "_id": _id, "method": "PUT", "body": {"desc": "new"}, "skipped": [],
            "before": {"_id": _id, "desc": "old", "readme": "", "files": [], "bids": None},
            "size_before": 100, "size_after": 110}


def test_desired_only_sends_editable_fields():
    assert set(dtsync.desired(REC, LIVE, "u")) <= {"desc", "readme", "files", "bids"}


def test_desired_never_touches_protected_file_fields():
    body = dtsync.desired(REC, LIVE, "u")
    keys = ("id", "filename", "dirname", "required")
    for old, new in zip(LIVE["files"], body["files"]):
        assert {k: old.get(k) for k in keys} == {k: new.get(k) for k in keys}


def test_proposed_files_are_appended_optional():
    r = copy.deepcopy(REC)
    r["files"].append({"id": "dwi_json", "filename": "dwi.json", "desc": "Sidecar.", "required": False, "proposed": True})
    body = dtsync.desired(r, LIVE, "u")
    assert body["files"][-1] == {"id": "dwi_json", "filename": "dwi.json", "desc": "Sidecar.", "required": False}
    assert len(body["files"]) == len(LIVE["files"]) + 1


def test_existing_bids_maps_are_kept():
    body = dtsync.desired(REC, LIVE, "u")
    assert body["bids"]["maps"][: len(LIVE["bids"]["maps"])] == LIVE["bids"]["maps"]


def test_drifted_field_is_skipped():
    at_pull = {"_id": "1", "name": "neuro/dwi", "desc": "old", "readme": "", "files": [], "bids": None}
    now = dict(at_pull, desc="edited by an admin")
    ch = dtsync.plan({"neuro/dwi": REC}, {"neuro/dwi": now}, {"neuro/dwi": at_pull}, "u")[0]
    assert "desc" in ch["skipped"] and "desc" not in ch["body"]


def test_draft_becomes_post():
    d = copy.deepcopy(REC)
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = "neuro/anat/angio"
    ch = dtsync.plan({"neuro/anat/angio": d}, {}, {}, "u")[0]
    assert ch["method"] == "POST" and ch["body"]["name"] == "neuro/anat/angio"


def test_budget_blocks_large_record():
    big = [{"name": "x", "size_before": 1000, "size_after": 5000}]
    assert dtsync.check_budget(big, approve_size=False)
    assert dtsync.check_budget(big, approve_size=True) == []


def test_budget_blocks_total_growth_over_25_percent():
    grow = [{"name": str(i), "size_before": 1000, "size_after": 1300} for i in range(3)]
    assert dtsync.check_budget(grow, approve_size=False)
    ok = [{"name": str(i), "size_before": 1000, "size_after": 1200} for i in range(3)]
    assert dtsync.check_budget(ok, approve_size=False) == []


def test_undo_log_written_before_each_send(tmp_path):
    http = RecordingHttp(fail_on_put=2)
    with pytest.raises(RuntimeError):
        dtsync.push([_change("a", "1" * 24), _change("b", "2" * 24)], http, tmp_path / "undo.json")
    assert len(json.loads((tmp_path / "undo.json").read_text())) == 2


def test_undo_restores_before_values(tmp_path):
    log = tmp_path / "undo.json"
    dtsync.push([_change("a", "1" * 24)], RecordingHttp(), log)
    http = RecordingHttp()
    dtsync.undo(log, http)
    assert http.puts[0] == (f"/datatype/{'1' * 24}", {"desc": "old", "readme": "", "files": [], "bids": None})


def test_undo_keeps_created_datatype_that_is_in_use(tmp_path):
    log = tmp_path / "undo.json"
    post = dict(_change("n", None), method="POST", before=None, body={"name": "n"})
    dtsync.push([post], RecordingHttp(), log)
    http = RecordingHttp(found=1)
    dtsync.undo(log, http)
    assert http.deletes == []
