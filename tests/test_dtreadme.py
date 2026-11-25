import copy
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtreadme  # noqa: E402
import dtrecord  # noqa: E402

DWI = dtrecord.load(ROOT / "tests" / "fixtures" / "dt-neuro.dwi.json")
URL = "https://github.com/brainlife/abcd-spec/blob/master/datatypes/neuro.dwi.json"


def test_render_is_small_and_links_catalog():
    md = dtreadme.render(DWI, URL)
    assert len(md.encode()) <= dtreadme.SUMMARY_MAX_BYTES
    assert md.rstrip().endswith("datatypes/neuro.dwi.json")


def test_render_covers_use_bids_sharing_and_app_counts():
    md = dtreadme.render(DWI, URL)
    assert "**Use for:** Tractography and microstructure modelling." in md
    assert "**Not for:** Analyses needing raw k-space data." in md
    assert "dwi/dwi (equivalent)" in md
    assert "Tier 2" in md
    assert "Input to 1 App" in md


def test_render_leaves_file_and_app_lists_to_the_catalog():
    md = dtreadme.render(DWI, URL)
    assert "dwi.nii.gz" not in md and "dMRI preprocessing" not in md


def test_existing_readme_is_replaced_by_the_summary():
    r = copy.deepcopy(DWI)
    r["brainlife"]["original"]["readme"] = "Hand-written notes."
    assert dtreadme.render(r, URL) == dtreadme.render(DWI, URL)


def test_long_existing_readme_is_replaced_too():
    r = copy.deepcopy(DWI)
    r["brainlife"]["original"]["readme"] = "é" * 3000
    md = dtreadme.render(r, URL)
    assert "é" not in md and len(md.encode()) <= dtreadme.SUMMARY_MAX_BYTES


def test_long_use_lists_are_cut_to_fit():
    r = copy.deepcopy(DWI)
    r["usage"]["intended_use"] = ["x" * 400, "y" * 400]
    assert len(dtreadme.render(r, URL).encode()) <= dtreadme.SUMMARY_MAX_BYTES


def test_generated_text_is_not_mistaken_for_a_hand_written_readme():
    assert dtreadme.strip_generated(dtreadme.render(DWI, URL)) == ""
    old = "Hand-written notes.\n\n**Sharing:** Tier 2 (x) by default.\n\nFull record: " + URL
    assert dtreadme.strip_generated(old) == "Hand-written notes."
