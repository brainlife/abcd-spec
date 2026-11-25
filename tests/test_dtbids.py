import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtbids  # noqa: E402
import dtrecord  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
MINI = json.loads((FIX / "bids-schema-mini.json").read_text())
DWI = dtrecord.load(FIX / "dt-neuro.dwi.json")


def _draft():
    d = copy.deepcopy(DWI)
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = "neuro/anat/angio"
    d["bids"]["correspondences"][0].update(datatype="anat", suffix="angio")
    return d


def test_index_has_t1w_and_dwi():
    idx = dtbids.bids_index(MINI)
    assert idx[("anat", "T1w")]["level"] == "raw"
    assert ".nii.gz" in idx[("dwi", "dwi")]["extensions"]
    assert "subject" in idx[("anat", "T1w")]["entities"]


def test_index_has_derivatives():
    assert dtbids.bids_index(MINI)[("anat", "dseg")]["level"] == "derivative"


def test_existing_maps_kept_in_order_new_ones_appended():
    live = {"derivatives": "dwi", "maps": [{"_id": "m1", "src": "dwi.nii.gz", "dest": "dwi.nii.gz"}]}
    out = dtbids.project_maps(DWI, live)
    assert out["maps"][0] == live["maps"][0]
    assert [m["src"] for m in out["maps"]].count("dwi.nii.gz") == 1
    assert {"src": "dwi.bvecs", "dest": "dwi.bvec"} in out["maps"]
    assert out["derivatives"] == "dwi"


def test_meta_sidecar_becomes_meta_map():
    out = dtbids.project_maps(DWI, None)
    assert {"src": "_meta_", "dest": "dwi.json"} in out["maps"]


def test_live_derivatives_is_not_overwritten():
    out = dtbids.project_maps(DWI, {"derivatives": "custom", "maps": []})
    assert out["derivatives"] == "custom"


def test_match_none_produces_no_maps():
    r = copy.deepcopy(DWI)
    r["bids"]["correspondences"][0]["match"] = "none"
    assert dtbids.project_maps(r, None)["maps"] == []


def test_aimport_rows_mark_drafts():
    rows = dtbids.aimport_rows({"neuro/dwi": DWI, "neuro/anat/angio": _draft()})
    assert {r["status"] for r in rows} == {"active", "draft"}
    assert {"bids": {"datatype": "dwi", "suffix": "dwi"},
            "brainlife": {"datatype": "neuro/dwi", "tags": []}, "status": "active"} in rows


def test_unmapped_lists_bids_pairs_without_a_record():
    missing = dtbids.unmapped(dtbids.bids_index(MINI), {"neuro/dwi": DWI})
    assert ("anat", "T1w") in missing and ("dwi", "dwi") not in missing
