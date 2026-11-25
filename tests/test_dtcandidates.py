import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtbids  # noqa: E402
import dtcandidates  # noqa: E402
import dtrecord  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
MINI = json.loads((FIX / "bids-schema-mini.json").read_text())
DWI = dtrecord.load(FIX / "dt-neuro.dwi.json")


def _draft(name, datatype, suffix):
    d = copy.deepcopy(DWI)
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = name
    d["bids"]["correspondences"][0].update(datatype=datatype, suffix=suffix, match="TODO")
    return d


def _rows(records):
    return {r["proposed"] or r["bids"]: r for r in dtcandidates.candidates(records, dtbids.bids_index(MINI))}


def test_new_bids_suffix_is_recommended_for_creation():
    rows = _rows({"neuro/dwi": DWI, "neuro/anat/t2w": _draft("neuro/anat/t2w", "anat", "T2w")})
    assert rows["neuro/anat/t2w"]["recommendation"] == "create"
    assert rows["neuro/anat/t2w"]["tier"] == 3


def test_draft_whose_name_exists_in_other_case_is_merge():
    existing = copy.deepcopy(DWI)
    existing["brainlife"]["name"] = "neuro/perf/ASL"
    rows = _rows({"neuro/perf/ASL": existing, "neuro/perf/asl": _draft("neuro/perf/asl", "perf", "asl")})
    assert rows["neuro/perf/asl"]["recommendation"].startswith("merge into neuro/perf/ASL")


def test_draft_already_covered_by_a_registered_datatype_is_skip():
    rows = _rows({"neuro/dwi": DWI, "neuro/dwi/raw": _draft("neuro/dwi/raw", "dwi", "dwi")})
    assert rows["neuro/dwi/raw"]["recommendation"].startswith("skip: covered by neuro/dwi")


def test_bids_pair_without_any_record_is_listed():
    rows = _rows({"neuro/dwi": DWI})
    assert rows["anat/T1w"]["recommendation"] == "no draft yet"


def test_markdown_has_one_row_per_candidate():
    rows = dtcandidates.candidates({"neuro/dwi": DWI}, dtbids.bids_index(MINI))
    md = dtcandidates.render(rows)
    assert md.count("\n| ") == len(rows)  # one line per candidate after the header
