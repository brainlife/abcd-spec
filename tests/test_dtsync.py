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
    body = dtsync.desired(r, dict(LIVE, validator=None), "u")
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


def _angio_draft():
    d = copy.deepcopy(REC)
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = "neuro/anat/angio"
    d["files"][0]["proposed"] = True
    return d


def test_draft_becomes_post_with_its_files_and_admins():
    ch = dtsync.plan({"neuro/anat/angio": _angio_draft()}, {}, {}, "u", admins=("1",))[0]
    assert ch["method"] == "POST" and ch["body"]["name"] == "neuro/anat/angio"
    assert [f["id"] for f in ch["body"]["files"]] == [f["id"] for f in REC["files"]]
    assert all("proposed" not in f for f in ch["body"]["files"])
    assert ch["body"]["admins"] == ["1"]


def test_draft_post_requires_admins():
    with pytest.raises(ValueError):
        dtsync.plan({"neuro/anat/angio": _angio_draft()}, {}, {}, "u")


def test_draft_post_refused_when_name_is_already_live():
    with pytest.raises(ValueError):
        dtsync.plan({"neuro/anat/angio": _angio_draft()}, {"neuro/anat/angio": dict(LIVE, name="neuro/anat/angio")},
                    {}, "u", admins=("1",))


def _rec_drafted_against(live):
    r = copy.deepcopy(REC)
    r["brainlife"]["original"] = {"desc": live["desc"], "readme": live.get("readme") or "",
                                  "file_descs": {f["id"]: f.get("desc", "") for f in live["files"]}}
    return r


def test_edit_made_between_draft_and_pull_is_skipped():
    now = dict(LIVE, desc="edited by an admin", readme="admin readme",
               files=[dict(LIVE["files"][0], desc="admin file desc")] + LIVE["files"][1:])
    ch = dtsync.plan({"neuro/dwi": _rec_drafted_against(LIVE)}, {"neuro/dwi": now}, {"neuro/dwi": now}, "u")[0]
    assert {"desc", "readme", "files"} <= set(ch["skipped"])
    assert not {"desc", "readme", "files"} & set(ch["body"])


def test_proposed_files_wait_when_the_datatype_has_a_validator():
    r = copy.deepcopy(REC)
    r["files"].append({"id": "x_json", "filename": "x.json", "desc": "Sidecar.", "required": False, "proposed": True})
    body = dtsync.desired(r, dict(LIVE, validator="brainlife/validator-x"), "u")
    assert "x_json" not in [f["id"] for f in body["files"]]


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


def test_undo_restores_only_the_fields_push_wrote(tmp_path):
    log = tmp_path / "undo.json"
    dtsync.push([_change("a", "1" * 24)], RecordingHttp(), log)
    http = RecordingHttp()
    dtsync.undo(log, http)
    assert http.puts[0] == (f"/datatype/{'1' * 24}", {"desc": "old"})


def test_push_reports_each_created_datatype_as_it_goes(tmp_path):
    seen = []
    post = dict(_change("n", None), method="POST", before=None, body={"name": "n"})
    http = RecordingHttp(fail_on_put=1)
    with pytest.raises(RuntimeError):
        dtsync.push([post, _change("a", "1" * 24)], http, tmp_path / "undo.json",
                    on_created=lambda name, _id: seen.append((name, _id)))
    assert seen == [("n", "0" * 24)]


def test_undo_keeps_created_datatype_that_is_in_use(tmp_path):
    log = tmp_path / "undo.json"
    post = dict(_change("n", None), method="POST", before=None, body={"name": "n"})
    dtsync.push([post], RecordingHttp(), log)
    http = RecordingHttp(found=1)
    dtsync.undo(log, http)
    assert http.deletes == []


def test_budget_allows_an_oversized_record_that_shrinks():
    assert dtsync.check_budget([{"name": "x", "size_before": 7000, "size_after": 6900}], approve_size=False) == []


def test_our_pushed_summary_is_not_an_edit():
    import dtreadme
    r = _rec_drafted_against(LIVE)
    r["brainlife"]["original"]["readme"] = "Hand-written notes."
    now = dict(LIVE, readme=dtreadme.render(r, "u"))
    ch = dtsync.plan({"neuro/dwi": r}, {"neuro/dwi": now}, {"neuro/dwi": now}, "u")
    assert all("readme" not in c["skipped"] for c in ch)


def test_our_pushed_desc_and_file_descs_are_not_edits():
    r = _rec_drafted_against(LIVE)
    now = dict(LIVE, desc=r["brainlife"]["desc"],
               files=[dict(f, desc=next(x["desc"] for x in r["files"] if x["id"] == f["id"])) for f in LIVE["files"]])
    ch = dtsync.plan({"neuro/dwi": r}, {"neuro/dwi": now}, {"neuro/dwi": now}, "u")
    assert all(not ({"desc", "files"} & set(c["skipped"])) for c in ch)
