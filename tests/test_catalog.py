import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import blapp  # noqa: E402
import catalog  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def _manifest():
    record = json.loads((FIX / "freesurfer-7.3.2.registry.json").read_text())
    return blapp.generate(record, main_text=(FIX / "freesurfer.main").read_text())


def test_index_entry_is_compact_and_searchable():
    entry = catalog.index_entry(_manifest())
    assert entry["id"] == json.loads((FIX / "freesurfer-7.3.2.registry.json").read_text())["_id"]
    assert entry["name"] == "Freesurfer 7.3.2"
    assert entry["github"] == "brainlife/app-freesurfer"
    assert entry["branch"] == "7.3.2"
    assert entry["inputs"] == ["neuro/anat/t1w", "neuro/anat/t2w"]
    assert "neuro/freesurfer" in entry["outputs"]
    assert entry["deprecated"] is False
    assert entry["unknowns"] > 0
    assert entry["manifest"] == f"apps/{entry['id']}.json"


def test_build_writes_one_file_per_app_and_an_index(tmp_path):
    m = _manifest()
    other = dict(m, registry=dict(m["registry"], id="other"), name="Other", deprecated_by="x")
    catalog.build([m, other], tmp_path)
    assert json.loads((tmp_path / "apps" / f"{m['registry']['id']}.json").read_text()) == m
    index = json.loads((tmp_path / "index.json").read_text())
    assert index["spec"] == "brainlife-app/2.0"
    assert [a["name"] for a in index["apps"]] == ["Freesurfer 7.3.2", "Other"]
    assert index["apps"][1]["deprecated"] is True


def test_build_refuses_invalid_manifests(tmp_path):
    m = _manifest()
    m["inputs"][0]["datatype"] = "neuro/does-not-exist"
    try:
        catalog.build([m], tmp_path)
    except ValueError as e:
        assert "neuro/does-not-exist" in str(e)
    else:
        raise AssertionError("invalid manifest was accepted")
