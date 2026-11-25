import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import bldt  # noqa: E402
import dtrecord  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
SNAP = json.loads((FIX / "dt-api-snapshot.json").read_text())
MINI = json.loads((FIX / "bids-schema-mini.json").read_text())
APP_INDEX = json.loads((ROOT / "catalog" / "index.json").read_text())
DWI = dtrecord.load(FIX / "dt-neuro.dwi.json")
ROWS = [
    {"bids": {"datatype": "anat", "suffix": "T1w"}, "brainlife": {"datatype": "neuro/anat/t1w", "tags": []}, "status": "active"},
    {"bids": {"datatype": "dwi", "suffix": "dwi"}, "brainlife": {"datatype": "neuro/dwi", "tags": []}, "status": "active"},
    {"bids": {"datatype": "anat", "suffix": "angio"}, "brainlife": {"datatype": "neuro/anat/angio", "tags": []}, "status": "draft"},
]
ANGIO_AIMPORT_DRAFT = {
    "name": "neuro/anat/angio", "desc": "Magnetic resonance angiography.", "readme": "# draft", "draft": True,
    "bids_version": "1.11.2", "datatype_tags": [],
    "bids": {"derivatives": "anat", "maps": [{"src": "angio.nii.gz", "dest": "angio.nii.gz", "json": "angio.json"},
                                             {"src": "angio.json", "dest": "angio.json"}]},
    "files": [{"id": "nii_gz", "filename": "angio.nii.gz", "ext": ".nii.gz", "desc": "BIDS angio.nii.gz", "required": False},
              {"id": "json", "filename": "angio.json", "desc": "BIDS sidecar", "required": False}],
}


def _draft(existing=None):
    return bldt.draft(SNAP, MINI, APP_INDEX, ROWS, existing or {})


def test_every_drafted_record_validates():
    for name, r in _draft().items():
        assert dtrecord.validate(r) == [], name


def test_draft_keeps_reviewed_values():
    out = _draft({"neuro/dwi": DWI})
    assert out["neuro/dwi"]["brainlife"]["desc"] == DWI["brainlife"]["desc"]
    assert out["neuro/dwi"]["governance"] == DWI["governance"]


def test_draft_refreshes_original_from_live():
    stale = copy.deepcopy(DWI)
    stale["brainlife"]["original"]["desc"] = "stale"
    live_desc = next(d for d in SNAP["datatypes"] if d["name"] == "neuro/dwi")["desc"]
    assert _draft({"neuro/dwi": stale})["neuro/dwi"]["brainlife"]["original"]["desc"] == live_desc


def test_draft_marks_judgement_fields_todo():
    todo = _draft()["neuro/anat/t1w"]["provenance"]["todo"]
    assert "governance.default_tier" in todo and "usage.intended_use" in todo


def test_draft_lists_apps_from_catalog_index():
    out = _draft()
    assert any(a["name"] == "Freesurfer 7.3.2" for a in out["neuro/anat/t1w"]["usage"]["inputs_of"])


def test_draft_maps_bids_from_aimport_rows():
    c = _draft()["neuro/anat/t1w"]["bids"]["correspondences"][0]
    assert (c["datatype"], c["suffix"], c["level"]) == ("anat", "T1w", "raw")
    assert ".nii.gz" in c["extensions"]


def test_draft_handles_name_with_space():
    out = _draft()
    assert "zarr v3" in out and dtrecord.slug("zarr v3") == "zarr_v3"


def test_import_drafts_have_no_id(tmp_path):
    (tmp_path / "neuro.anat.angio.json").write_text(json.dumps(ANGIO_AIMPORT_DRAFT))
    d = bldt.import_drafts(tmp_path, MINI)["neuro/anat/angio"]
    assert "_id" not in d["brainlife"] and d["files"][0]["required"] is False
    assert dtrecord.validate(d) == []
    assert {"file_id": "json", "bids_part": "angio.json", "sidecar": "file"} in d["bids"]["correspondences"][0]["files"]


def test_generate_lists_registered_datatypes_and_renders_readmes():
    d = copy.deepcopy(DWI)
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = "neuro/anat/angio"
    records = {"neuro/dwi": copy.deepcopy(DWI), "neuro/anat/angio": d}
    listing = bldt.generate(records)
    assert listing == [{"id": DWI["brainlife"]["_id"], "name": "neuro/dwi"}]
    assert records["neuro/dwi"]["brainlife"]["readme"].rstrip().endswith("datatypes/neuro.dwi.json")


def test_get_json_sends_a_user_agent(monkeypatch):
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(req, timeout):
        seen["ua"] = req.get_header("User-agent")
        return Resp()

    monkeypatch.setattr(bldt.urllib.request, "urlopen", fake_urlopen)
    bldt._get_json("https://example.org/x.json")
    assert seen["ua"].startswith("brainlife-abcd-spec")


def test_draft_ignores_placeholder_aimport_rows():
    rows = ROWS + [{"bids": {"datatype": "anat", "suffix": "T2w"}, "brainlife": None, "status": "planned"}]
    out = bldt.draft(SNAP, MINI, APP_INDEX, rows, {})
    assert out["neuro/anat/t1w"]["bids"]["correspondences"][0]["suffix"] == "T1w"
