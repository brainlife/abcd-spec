import copy
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtreadme  # noqa: E402
import dtrecord  # noqa: E402

DWI = dtrecord.load(ROOT / "tests" / "fixtures" / "dt-neuro.dwi.json")
URL = "https://github.com/brainlife/abcd-spec/blob/master/datatypes/neuro.dwi.json"


def test_render_fits_budget_and_links_catalog():
    md = dtreadme.render(DWI, URL)
    assert len(md.encode()) <= 2048
    assert md.rstrip().endswith("datatypes/neuro.dwi.json")


def test_render_covers_files_apps_bids_and_sharing():
    md = dtreadme.render(DWI, URL)
    assert "dwi.nii.gz" in md
    assert "dMRI preprocessing" in md
    assert "dwi/dwi — equivalent" in md
    assert "Tier 2" in md


def test_long_original_readme_is_kept_byte_for_byte():
    r = copy.deepcopy(DWI)
    r["brainlife"]["original"]["readme"] = "é" * 1500
    assert dtreadme.render(r, "u") == "é" * 1500


def test_short_original_readme_comes_first():
    r = copy.deepcopy(DWI)
    r["brainlife"]["original"]["readme"] = "Hand-written notes."
    md = dtreadme.render(r, "u")
    assert md.startswith("Hand-written notes.") and "dwi.nii.gz" in md


def test_many_apps_are_truncated():
    r = copy.deepcopy(DWI)
    r["usage"]["inputs_of"] = [{"app_id": str(i), "name": f"App {i}", "purpose": "p"} for i in range(30)]
    assert "and 22 more" in dtreadme.render(r, "u")


def test_render_says_how_it_can_and_cannot_be_used():
    md = dtreadme.render(DWI, URL)
    assert "**Use for:** Tractography and microstructure modelling." in md
    assert "**Not for:** Analyses needing raw k-space data." in md
