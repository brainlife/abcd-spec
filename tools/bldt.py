#!/usr/bin/env python3
"""Maintain the brainlife.io datatype catalog (datatypes/).

    bldt.py pull                       snapshot brainlife.io datatypes into snapshots/<date>/
    bldt.py bids [--version stable]    save the BIDS schema into snapshots/
    bldt.py draft --snapshot S --bids B --aimport A.json
                                       create or refresh datatypes/<slug>.json
    bldt.py import-drafts DIR --bids B convert ezbids aimport datatype drafts into datatypes/drafts/
    bldt.py generate                   render readmes, rewrite schema/datatypes.json
    bldt.py diff [--only NAME]         what push would change on brainlife.io (read-only)
    bldt.py push [--only NAME] [--approve-size]
                                       write desc, readme, files and bids, with an undo log
    bldt.py push --drafts --admins SUBS register reviewed drafts as new datatypes
    bldt.py undo LOG                   restore the records listed in an undo log

Drafting fills what can be derived (ids, files, Apps that use the datatype, BIDS correspondences)
and marks judgement fields "TODO"; provenance.todo lists them. Values already reviewed in an
existing record are kept. Only push and undo write to brainlife.io.
"""
import argparse
import base64
import copy
import datetime
import json
import pathlib
import sys
import time
import urllib.request

import dtbids
import dtreadme
import dtrecord
import dtsync

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
        if not row.get("brainlife") or row["brainlife"]["datatype"] != name or not row["bids"].get("suffix"):
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


def generate(records):
    """Render each finished record's readme; return the schema/datatypes.json listing."""
    for record in records.values():
        if not record["provenance"]["todo"]:
            record["brainlife"]["readme"] = dtreadme.render(record, dtsync._catalog_url(dtsync.CATALOG_URL, record))
    return sorted(({"id": r["brainlife"]["_id"], "name": n} for n, r in records.items() if "_id" in r["brainlife"]),
                  key=lambda d: d["name"])


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "brainlife-abcd-spec bldt.py"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def pull(api=API, out=ROOT / "snapshots"):
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = pathlib.Path(out) / day / "datatypes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_get_json(f"{api}/datatype?limit=0"), indent=1) + "\n")
    return path


class Http:
    """Warehouse API with the token from `bl login` (~/.config/brainlife.io/.jwt)."""

    def __init__(self, api=API, token_path=pathlib.Path.home() / ".config" / "brainlife.io" / ".jwt"):
        try:
            self.token = pathlib.Path(token_path).read_text().strip()
            payload = self.token.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        except (OSError, IndexError, ValueError):
            sys.exit(f"No brainlife.io login token at {token_path}. Run `bl login` in a terminal first.")
        if claims.get("exp", 0) < time.time():
            sys.exit("The brainlife.io login token has expired. Run `bl login` in a terminal first.")
        self.api = api

    def _send(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.api + path, data=data, method=method,
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
        return json.loads(text) if text else None

    def get(self, path):
        return self._send("GET", path)

    def put(self, path, body):
        return self._send("PUT", path, body)

    def post(self, path, body):
        return self._send("POST", path, body)

    def delete(self, path):
        return self._send("DELETE", path)


def _latest_snapshot():
    snaps = sorted((ROOT / "snapshots").glob("*/datatypes.json"))
    if not snaps:
        sys.exit("No snapshot; run `bldt.py pull` first.")
    return {d["name"]: d for d in json.loads(snaps[-1].read_text())["datatypes"]}


def _changes(only, drafts, admins):
    records = dtrecord.load_all(ROOT / "datatypes")
    records = {n: r for n, r in records.items() if ("_id" in r["brainlife"]) != drafts and (not only or n in only)}
    unfinished = [n for n, r in records.items() if r["provenance"]["todo"] or dtrecord.validate(r)]
    if unfinished:
        sys.exit(f"Records with TODOs or errors: {', '.join(unfinished)}")
    live_now = {d["name"]: d for d in _get_json(f"{API}/datatype?limit=0")["datatypes"]}
    return dtsync.plan(records, live_now, _latest_snapshot(), admins=admins)


def _report(changes):
    for c in changes:
        skipped = f"  skipped (edited on brainlife.io since pull): {', '.join(c['skipped'])}" if c["skipped"] else ""
        print(f"{c['method']} {c['name']}: {', '.join(c['body']) or '-'}  {c['size_before']} -> {c['size_after']} bytes{skipped}")
    print(f"total {sum(c['size_before'] for c in changes)} -> {sum(c['size_after'] for c in changes)} bytes")


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
    for cmd in ("diff", "push"):
        c = sub.add_parser(cmd)
        c.add_argument("--only", action="append", default=[])
        c.add_argument("--drafts", action="store_true", help="register reviewed drafts (POST) instead")
        c.add_argument("--admins", default="", help="comma-separated auth subs for new datatypes")
        c.add_argument("--approve-size", action="store_true")
    sub.add_parser("generate")
    u = sub.add_parser("undo")
    u.add_argument("log")
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
    elif a.cmd in ("diff", "push"):
        changes = _changes(set(a.only), a.drafts, [s for s in a.admins.split(",") if s])
        _report(changes)
        errors = dtsync.check_budget(changes, a.approve_size)
        if errors:
            sys.exit("Size budget exceeded (use --approve-size after review):\n" + "\n".join(errors))
        if a.cmd == "push":
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            log = ROOT / "docs" / "backfill" / "datatypes" / f"{stamp}-undo.json"
            log.parent.mkdir(parents=True, exist_ok=True)
            created = dtsync.push(changes, Http(), log)
            for name, _id in created.items():
                old = root / "drafts" / f"{dtrecord.slug(name)}.json"
                record = dtrecord.load(old)
                record["brainlife"]["_id"] = _id
                dtrecord.save(root / old.name, record)
                old.unlink()
            print(f"undo log: {log}")
    elif a.cmd == "generate":
        records = dtrecord.load_all(root)
        listing = generate(records)
        _save_all(records, root)
        (ROOT / "schema" / "datatypes.json").write_text(json.dumps(listing, indent=1) + "\n")
        print(f"{len(listing)} datatypes listed, {len(records)} records")
    elif a.cmd == "undo":
        kept = dtsync.undo(a.log, Http())
        if kept:
            print(f"Kept (in use): {', '.join(kept)}")


if __name__ == "__main__":
    sys.exit(main())
