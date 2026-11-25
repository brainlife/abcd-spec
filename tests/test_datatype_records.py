import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import dtreadme  # noqa: E402
import dtrecord  # noqa: E402

RECORDS = dtrecord.load_all(ROOT / "datatypes")


def test_catalog_is_not_empty():
    assert len([r for r in RECORDS.values() if "_id" in r["brainlife"]]) >= 140


def test_every_record_is_valid_and_complete():
    for name, r in RECORDS.items():
        assert dtrecord.validate(r) == [], name
        if "_id" in r["brainlife"]:
            assert r["provenance"]["todo"] == [], name


def test_schema_datatypes_json_matches_records():
    ids = {r["brainlife"]["_id"]: n for n, r in RECORDS.items() if "_id" in r["brainlife"]}
    listed = {d["id"]: d["name"] for d in json.loads((ROOT / "schema" / "datatypes.json").read_text())}
    assert listed == ids


def test_rendered_readmes_fit_budget():
    for n, r in RECORDS.items():
        md = dtreadme.render(r, "u")
        assert len(md.encode()) <= 2048 or md == r["brainlife"]["original"]["readme"], n
