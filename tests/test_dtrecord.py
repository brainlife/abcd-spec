import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtrecord  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def _dwi():
    return dtrecord.load(FIX / "dt-neuro.dwi.json")


def test_slug_round_trips_unusual_names():
    assert dtrecord.slug("neuro/anat/t1w") == "neuro.anat.t1w"
    assert dtrecord.slug("zarr v3") == "zarr_v3"


def test_fixture_record_is_valid():
    assert dtrecord.validate(_dwi()) == []


def test_desc_over_200_chars_is_rejected():
    r = _dwi()
    r["brainlife"]["desc"] = "x" * 201
    assert any("desc" in e for e in dtrecord.validate(r))


def test_tier_outside_1_to_5_is_rejected():
    r = _dwi()
    r["governance"]["default_tier"] = 6
    assert dtrecord.validate(r)


def test_tier_placeholder_allowed_while_todo():
    r = _dwi()
    r["governance"]["default_tier"] = 0
    assert dtrecord.validate(r)
    r["provenance"]["todo"] = ["governance.default_tier"]
    assert dtrecord.validate(r) == []


def test_readme_over_2048_bytes_rejected_unless_original():
    r = _dwi()
    r["brainlife"]["readme"] = "é" * 1100  # 2200 bytes
    assert any("readme" in e for e in dtrecord.validate(r))
    r["brainlife"]["original"]["readme"] = r["brainlife"]["readme"]
    assert dtrecord.validate(r) == []


def test_record_size_uses_compact_json():
    assert dtrecord.record_size({"a": 1}) == len('{"a":1}')


def test_save_then_load_is_identical(tmp_path):
    r = _dwi()
    dtrecord.save(tmp_path / "x.json", r)
    assert dtrecord.load(tmp_path / "x.json") == r


def test_load_all_reads_records_and_drafts(tmp_path):
    r = _dwi()
    dtrecord.save(tmp_path / "neuro.dwi.json", r)
    d = _dwi()
    del d["brainlife"]["_id"]
    d["brainlife"]["name"] = "zarr v3"
    (tmp_path / "drafts").mkdir()
    dtrecord.save(tmp_path / "drafts" / "zarr_v3.json", d)
    assert set(dtrecord.load_all(tmp_path)) == {"neuro/dwi", "zarr v3"}
