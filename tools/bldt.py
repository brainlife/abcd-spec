#!/usr/bin/env python3
"""Maintain the brainlife.io datatype catalog (datatypes/).

    bldt.py pull                       snapshot brainlife.io datatypes into snapshots/<date>/
    bldt.py bids [--version stable]    save the BIDS schema into snapshots/
    bldt.py draft --snapshot S --bids B --aimport A.json
                                       create or refresh datatypes/<slug>.json
    bldt.py import-drafts DIR --bids B convert ezbids aimport datatype drafts into datatypes/drafts/

Drafting fills what can be derived (ids, files, Apps that use the datatype, BIDS correspondences)
and marks judgement fields "TODO"; provenance.todo lists them. Values already reviewed in an
existing record are kept. Nothing here writes to brainlife.io.
"""
import argparse
import copy
import datetime
import json
import pathlib
import sys
import urllib.request

import dtbids
import dtrecord

ROOT = dtrecord.ROOT
API = "https://brainlife.io/api/warehouse"
BIDS_SCHEMA_URL = "https://bids-specification.readthedocs.io/en/{version}/schema.json"
TODO = dtrecord.TODO


def _governance_todo():
    return {"human_neurodata": TODO, "default_tier": 0, "tier_conditions": [TODO], "information_kinds": [],
            "identifying_risks": [TODO], "sharing_cautions": [TODO], "rationale": TODO}


def todo_fields(record):
    """Dotted paths of fields still holding a placeholder."""
    found = []

    def walk(value, path):
        if value == TODO or value == [TODO]:
            found.append(path)
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]")

    walk({k: v for k, v in record.items() if k != "provenance"}, "")
    if record["governance"]["default_tier"] == 0:
        found.append("governance.default_tier")
    return sorted(set(found))


def _apps(app_index, name, key, existing):
    purposes = {a["app_id"]: a["purpose"] for a in existing}
    return [{"app_id": a["id"], "name": a["name"].strip(), "purpose": purposes.get(a["id"], TODO)}
            for a in app_index["apps"] if name in a[key] and not a["deprecated"]]


def _correspondences(name, live, index, rows):
    files_by_src = {f.get("filename") or f.get("dirname"): f["id"] for f in live.get("files", [])}
    maps = (live.get("bids") or {}).get("maps") or []
    out = []
    for row in rows:
        if row["brainlife"]["datatype"] != name or not row["bids"].get("suffix"):
            continue
        key = (row["bids"]["datatype"], row["bids"]["suffix"])
        bids = index.get(key, {"extensions": [], "entities": [], "level": "raw"})
        out.append({"datatype": key[0], "suffix": key[1], "extensions": bids["extensions"],
                    "entities": bids["entities"], "level": bids["level"], "match": TODO,
                    "files": [], "tags": list(row["brainlife"].get("tags") or []), "notes": ""})
    if not out and maps:
        stem = maps[0]["dest"].split(".")[0]
        datatype = (live.get("bids") or {}).get("derivatives") or ""
        bids = index.get((datatype, stem), {"extensions": [], "entities": [], "level": "derivative"})
        out.append({"datatype": datatype, "suffix": stem, "extensions": bids["extensions"],
                    "entities": bids["entities"], "level": bids["level"], "match": TODO,
                    "files": [], "tags": [], "notes": "from the existing bids.maps on brainlife.io"})
    if out:
        for m in maps:
            if m["src"] == "_meta_":
                out[0]["files"].append({"file_id": "_meta_", "bids_part": m["dest"], "sidecar": "meta"})
            elif m["src"] in files_by_src:
                out[0]["files"].append({"file_id": files_by_src[m["src"]], "bids_part": m["dest"]})
    return out


def _new_record(live, app_index, index, rows):
    name = live["name"]
    return {
        "spec": "brainlife-datatype-record/1.0",
        "brainlife": {"_id": live["_id"], "name": name, "desc": TODO, "readme": live.get("readme") or "",
                      "original": {"desc": live.get("desc") or "", "readme": live.get("readme") or ""}},
        "files": [{k: f[k] for k in ("id", "filename", "dirname", "ext") if f.get(k)}
                  | {"desc": f.get("desc") or TODO, "required": bool(f.get("required"))}
                  for f in live.get("files", [])],
        "usage": {"inputs_of": _apps(app_index, name, "inputs", []),
                  "outputs_of": _apps(app_index, name, "outputs", []),
                  "intended_use": [TODO], "not_suitable_for": [TODO]},
        "bids": {"correspondences": _correspondences(name, live, index, rows), "checked_against": {}},
        "governance": _governance_todo(),
        "provenance": {"drafted_by": "tools/bldt.py draft", "sources": [f"{API}/datatype", "catalog/index.json"],
                       "todo": []},
    }


def _refresh(old, live, app_index):
    r = copy.deepcopy(old)
    bl = r["brainlife"]
    bl["_id"], bl["name"] = live["_id"], live["name"]
    bl["original"] = {"desc": live.get("desc") or "", "readme": live.get("readme") or ""}
    old_files = {f["id"]: f for f in old["files"]}
    files = []
    for f in live.get("files", []):
        entry = {k: f[k] for k in ("id", "filename", "dirname", "ext") if f.get(k)}
        entry["desc"] = old_files.get(f["id"], {}).get("desc") or f.get("desc") or TODO
        entry["required"] = bool(f.get("required"))
        files.append(entry)
    live_ids = {f["id"] for f in files}
    files += [f for f in old["files"] if f.get("proposed") and f["id"] not in live_ids]
    r["files"] = files
    r["usage"]["inputs_of"] = _apps(app_index, live["name"], "inputs", old["usage"]["inputs_of"])
    r["usage"]["outputs_of"] = _apps(app_index, live["name"], "outputs", old["usage"]["outputs_of"])
    return r


def _finish(record, schema):
    record["bids"]["checked_against"] = {"bids_version": schema["bids_version"],
                                         "schema_version": schema["schema_version"]}
    record["provenance"]["todo"] = todo_fields(record)
    return record


def draft(snapshot, bids_schema, app_index, aimport_rows, existing):
    index = dtbids.bids_index(bids_schema)
    out = {}
    for live in snapshot["datatypes"]:
        name = live["name"]
        if name in existing:
            record = _refresh(existing[name], live, app_index)
        else:
            record = _new_record(live, app_index, index, aimport_rows)
        out[name] = _finish(record, bids_schema)
    return out


def import_drafts(directory, bids_schema):
    """ezbids aimport datatype_drafts/*.json -> draft records (no brainlife._id)."""
    index = dtbids.bids_index(bids_schema)
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*.json")):
        d = json.loads(path.read_text())
        live = dict(d, _id=None)
        maps = d["bids"]["maps"]
        stem = maps[0]["dest"].split(".")[0] if maps else ""
        row = {"bids": {"datatype": d["bids"].get("derivatives", ""), "suffix": stem},
               "brainlife": {"datatype": d["name"], "tags": d.get("datatype_tags", [])}}
        record = _new_record(live, {"apps": []}, index, [row])
        del record["brainlife"]["_id"]
        record["brainlife"]["original"] = {"desc": "", "readme": ""}
        record["brainlife"]["readme"] = ""
        for c in record["bids"]["correspondences"]:
            for f in c["files"]:
                if f["bids_part"].endswith((".json", ".tsv")):
                    f["sidecar"] = "file"
        record["provenance"]["drafted_by"] = "ezbids aimport/tools/draft_datatypes.py, imported by tools/bldt.py"
        record["provenance"]["sources"] = [f"ezbids aimport datatype_drafts/{path.name}"]
        out[d["name"]] = _finish(record, bids_schema)
    return out


def _get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def pull(api=API, out=ROOT / "snapshots"):
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = pathlib.Path(out) / day / "datatypes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_get_json(f"{api}/datatype?limit=0"), indent=1) + "\n")
    return path


def _save_all(records, root):
    for name, r in records.items():
        folder = root if "_id" in r["brainlife"] else root / "drafts"
        folder.mkdir(parents=True, exist_ok=True)
        dtrecord.save(folder / f"{dtrecord.slug(name)}.json", r)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull")
    b = sub.add_parser("bids")
    b.add_argument("--version", default="stable")
    d = sub.add_parser("draft")
    d.add_argument("--snapshot", required=True)
    d.add_argument("--bids", required=True)
    d.add_argument("--aimport", required=True, help="bids_brainlife_map.yaml converted to JSON")
    i = sub.add_parser("import-drafts")
    i.add_argument("directory")
    i.add_argument("--bids", required=True)
    a = p.parse_args(argv)
    root = ROOT / "datatypes"
    if a.cmd == "pull":
        print(pull())
    elif a.cmd == "bids":
        schema = _get_json(BIDS_SCHEMA_URL.format(version=a.version))
        path = ROOT / "snapshots" / f"bids-schema-{schema['bids_version']}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(schema) + "\n")
        print(path)
    elif a.cmd == "draft":
        load = lambda f: json.loads(pathlib.Path(f).read_text())  # noqa: E731
        existing = dtrecord.load_all(root) if root.exists() else {}
        records = draft(load(a.snapshot), load(a.bids), load(ROOT / "catalog" / "index.json"),
                        load(a.aimport)["mappings"], existing)
        _save_all(records, root)
        print(f"{len(records)} records, {sum(bool(r['provenance']['todo']) for r in records.values())} with TODOs")
    elif a.cmd == "import-drafts":
        existing = dtrecord.load_all(root) if root.exists() else {}
        drafts = {n: r for n, r in import_drafts(a.directory, json.loads(pathlib.Path(a.bids).read_text())).items()
                  if n not in existing}
        _save_all(drafts, root)
        print(f"{len(drafts)} drafts")


if __name__ == "__main__":
    sys.exit(main())
