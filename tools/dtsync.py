"""Plan, check and apply catalog changes to datatypes on brainlife.io.

Only desc, readme, files and bids are ever sent for an existing datatype. Existing file entries
keep id, filename, dirname and required; existing bids maps are kept. A field edited on
brainlife.io since the record was drafted or since the last pull is skipped and reported. Every write is logged (with the record
as it was) before it is sent, so an interrupted run can be undone.
"""
import json
import pathlib
import urllib.parse

import dtbids
import dtrecord
import dtreadme

EDITABLE = ("desc", "readme", "files", "bids")
RECORD_MAX = 4096
TOTAL_GROWTH = 1.25
CATALOG_URL = "https://github.com/brainlife/abcd-spec/blob/master/datatypes"


def _catalog_url(base, record):
    folder = "" if "_id" in record["brainlife"] else "drafts/"
    return f"{base}/{folder}{dtrecord.slug(record['brainlife']['name'])}.json"


def desired(record, live, catalog_url):
    """What brainlife.io should hold. Proposed (new, optional) files wait while the datatype has a
    validator, until someone confirms the validator accepts them."""
    descs = {f["id"]: f["desc"] for f in record["files"]}
    files = [dict(f, desc=descs.get(f["id"], f.get("desc", ""))) for f in live.get("files", [])]
    live_ids = {f["id"] for f in files}
    for f in record["files"]:
        if f.get("proposed") and f["id"] not in live_ids and not live.get("validator"):
            files.append(dict({k: v for k, v in f.items() if k != "proposed"}, required=False))
    return {"desc": record["brainlife"]["desc"], "readme": dtreadme.render(record, catalog_url),
            "files": files, "bids": dtbids.project_maps(record, live.get("bids"))}


def _strip_ids(value):
    """Compare files/bids without the _id mongoose adds to every subdocument."""
    if isinstance(value, dict):
        return {k: _strip_ids(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [_strip_ids(v) for v in value]
    return value


def _edited_since_draft(record, now):
    """Fields someone changed on brainlife.io after the record was drafted from it."""
    original = record["brainlife"]["original"]
    edited = []
    if (now.get("desc") or "") not in (original["desc"], record["brainlife"]["desc"]):
        edited.append("desc")
    live_readme = dtreadme.strip_generated(now.get("readme") or "")
    if live_readme and live_readme != dtreadme.strip_generated(original["readme"]):
        edited.append("readme")  # an empty result means brainlife.io shows our own summary
    if "file_descs" in original:
        live_descs = {f["id"]: f.get("desc") or "" for f in now.get("files", [])}
        ours = {f["id"]: f["desc"] for f in record["files"]}
        if any(d not in (original["file_descs"].get(i, d), ours.get(i)) for i, d in live_descs.items()):
            edited.append("files")
    return edited


def plan(records, live_now, live_at_pull, catalog_base=CATALOG_URL, admins=()):
    changes = []
    for name, record in sorted(records.items()):
        url = _catalog_url(catalog_base, record)
        if "_id" not in record["brainlife"]:
            if not admins:
                raise ValueError(f"{name}: new datatypes need --admins")
            if name in live_now:
                raise ValueError(f"{name}: already on brainlife.io; record its _id instead of creating it again")
            body = {"name": name, "desc": record["brainlife"]["desc"], "readme": dtreadme.render(record, url),
                    "files": [{k: v for k, v in f.items() if k != "proposed"} for f in record["files"]],
                    "bids": dtbids.project_maps(record, None), "datatype_tags": [], "admins": list(admins)}
            changes.append({"name": name, "_id": None, "method": "POST", "body": body, "skipped": [],
                            "before": None, "size_before": 0, "size_after": dtrecord.record_size(body)})
            continue
        now, then = live_now[name], live_at_pull.get(name, live_now[name])
        want = desired(record, now, url)
        body, skipped = {}, []
        edited = _edited_since_draft(record, now)
        for k in EDITABLE:
            if k in edited or _strip_ids(now.get(k)) != _strip_ids(then.get(k)):
                skipped.append(k)
            elif _strip_ids(want[k]) != _strip_ids(now.get(k)):
                body[k] = want[k]
        if body or skipped:
            changes.append({"name": name, "_id": now["_id"], "method": "PUT", "body": body, "skipped": skipped,
                            "before": {k: now.get(k) for k in ("_id",) + EDITABLE},
                            "size_before": dtrecord.record_size(now),
                            "size_after": dtrecord.record_size(dict(now, **body))})
    return changes


def check_budget(changes, approve_size):
    if approve_size:
        return []
    errors = [f"{c['name']}: {c['size_after']} bytes (limit {RECORD_MAX})"
              for c in changes if c["size_after"] > RECORD_MAX and c["size_after"] > c["size_before"]]
    before = sum(c["size_before"] for c in changes)
    after = sum(c["size_after"] for c in changes)
    if before and after > before * TOTAL_GROWTH:
        errors.append(f"total grows from {before} to {after} bytes (over {int((TOTAL_GROWTH - 1) * 100)}%)")
    return errors


def _log(path, entries):
    pathlib.Path(path).write_text(json.dumps(entries, indent=1) + "\n")


def push(changes, http, undo_path, on_created=None):
    """Apply changes in order; returns {name: new _id} for created datatypes.

    on_created(name, _id) runs right after each datatype is created, so an interrupted run never
    leaves a created datatype looking like an unsent draft."""
    entries, created = [], {}
    for c in changes:
        if not c["body"]:
            continue
        entry = {"name": c["name"], "_id": c["_id"], "method": c["method"], "fields": sorted(c["body"]),
                 "before": c["before"]}
        entries.append(entry)
        _log(undo_path, entries)
        if c["method"] == "POST":
            entry["_id"] = created[c["name"]] = http.post("/datatype", c["body"])["_id"]
            _log(undo_path, entries)
            if on_created:
                on_created(c["name"], entry["_id"])
        else:
            http.put(f"/datatype/{c['_id']}", c["body"])
    return created


def _in_use(http, _id):
    q = urllib.parse.quote
    datasets = http.get(f"/dataset?find={q(json.dumps({'datatype': _id}))}&limit=1")
    apps = http.get("/app?find=" + q(json.dumps({"$or": [{"inputs.datatype": _id}, {"outputs.datatype": _id}]}))
                    + "&limit=1")
    return bool(datasets.get("count") or apps.get("count"))


def undo(undo_path, http):
    """Restore every logged record; returns names of created datatypes kept because they are in use."""
    kept = []
    for e in reversed(json.loads(pathlib.Path(undo_path).read_text())):
        if e["method"] == "PUT":
            http.put(f"/datatype/{e['_id']}", {k: e["before"].get(k) for k in e.get("fields", EDITABLE)})
        elif e.get("_id"):
            if _in_use(http, e["_id"]):
                kept.append(e["name"])
            else:
                http.delete(f"/datatype/{e['_id']}")
    return kept


def validator_rules(records):
    """rules.json for brainlife/validator-catalog: each registered datatype's file list."""
    keys = ("id", "filename", "dirname", "required")
    return {r["brainlife"]["_id"]: {"name": name, "files": [{k: f[k] for k in keys if k in f} for f in r["files"]]}
            for name, r in sorted(records.items()) if "_id" in r["brainlife"]}


def plan_validator(live_now, service, branch):
    """PUT changes that attach a validator to datatypes that have none (never replaces one)."""
    return [{"name": name, "_id": d["_id"], "method": "PUT", "skipped": [],
             "body": {"validator": service, "validator_branch": branch},
             "before": {"_id": d["_id"], "validator": d.get("validator"), "validator_branch": d.get("validator_branch")},
             "size_before": dtrecord.record_size(d), "size_after": dtrecord.record_size(d)}
            for name, d in sorted(live_now.items()) if not d.get("validator")]
