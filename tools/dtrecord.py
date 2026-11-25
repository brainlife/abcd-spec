"""Load, save and validate datatype catalog records (datatypes/<slug>.json).

A record describes one brainlife.io datatype: the text written back to brainlife.io, its files,
which Apps use it, how it maps to BIDS, and governance defaults. Drafts (datatypes not yet on
brainlife.io) live in datatypes/drafts/ and have no brainlife._id.
"""
import json
import pathlib

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "datatype-record-1.0.schema.json").read_text())
README_MAX_BYTES = 2048
TODO = "TODO"


def slug(name):
    return name.replace("/", ".").replace(" ", "_")


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def save(path, record):
    pathlib.Path(path).write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load_all(root):
    root = pathlib.Path(root)
    records = {}
    for path in sorted(root.glob("*.json")) + sorted((root / "drafts").glob("*.json")):
        r = load(path)
        records[r["brainlife"]["name"]] = r
    return records


def record_size(api_record):
    return len(json.dumps(api_record, separators=(",", ":")))


def validate(record):
    errors = [f"{'.'.join(map(str, e.path)) or '<root>'}: {e.message}"
              for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(record)]
    if errors:
        return errors
    todo = set(record["provenance"]["todo"])
    if record["governance"]["default_tier"] == 0 and "governance.default_tier" not in todo:
        errors.append("governance.default_tier: must be 1-5 (0 only while listed in provenance.todo)")
    bl = record["brainlife"]
    if len(bl["readme"].encode()) > README_MAX_BYTES and bl["readme"] != bl["original"]["readme"]:
        errors.append(f"brainlife.readme: over {README_MAX_BYTES} bytes")
    return errors
