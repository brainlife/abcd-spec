"""BIDS side of the datatype catalog.

Reads the BIDS machine-readable schema (schema.json) into a (datatype, suffix) index, and projects
catalog records into the two shapes other code reads: warehouse's datatype.bids (maps used by the
BIDS export) and the rows of ezbids aimport's bids_brainlife_map.yaml.
"""
MAPPED = ("equivalent", "partial")


def _add_rules(index, rules, level):
    for rule in rules.values():
        if not isinstance(rule, dict) or "suffixes" not in rule:
            continue
        for datatype in rule.get("datatypes", []):
            for suffix in rule["suffixes"]:
                entry = index.setdefault((datatype, suffix), {"extensions": [], "entities": [], "level": level})
                entry["extensions"] += [e for e in rule.get("extensions", []) if e not in entry["extensions"]]
                entry["entities"] += [e for e in rule.get("entities", {}) if e not in entry["entities"]]


def bids_index(schema):
    """(datatype, suffix) -> {"extensions", "entities", "level"}; raw rules win over derivatives."""
    index = {}
    for group in schema["rules"]["files"]["raw"].values():
        _add_rules(index, group, "raw")
    for group in schema["rules"]["files"].get("deriv", {}).values():
        derived = {}
        _add_rules(derived, group, "derivative")
        for key, entry in derived.items():
            index.setdefault(key, entry)
    return index


def _mapped(record):
    return [c for c in record["bids"]["correspondences"] if c["match"] in MAPPED]


def project_maps(record, live_bids):
    """The datatype.bids object to write: live maps untouched and first, new maps appended."""
    live_bids = live_bids or {}
    maps = list(live_bids.get("maps") or [])
    sources = {m.get("src") for m in maps}
    files = {f["id"]: f.get("filename") or f.get("dirname") for f in record["files"]}
    correspondences = _mapped(record)
    for c in correspondences:
        for f in c["files"]:
            src = "_meta_" if f["file_id"] == "_meta_" else files.get(f["file_id"])
            if src is None or f.get("sidecar") == "missing" or src in sources:
                continue
            maps.append({"src": src, "dest": f["bids_part"]})
            sources.add(src)
    derivatives = live_bids.get("derivatives") or (correspondences[0]["datatype"] if correspondences else "")
    return {"derivatives": derivatives, "maps": maps}


def aimport_rows(records):
    rows = []
    for name, record in sorted(records.items()):
        status = "active" if "_id" in record["brainlife"] else "draft"
        for c in _mapped(record):
            rows.append({"bids": {"datatype": c["datatype"], "suffix": c["suffix"]},
                         "brainlife": {"datatype": name, "tags": list(c["tags"])}, "status": status})
    return rows


def unmapped(index, records):
    covered = {(c["datatype"], c["suffix"]) for r in records.values() for c in r["bids"]["correspondences"]}
    return sorted(k for k in index if k not in covered)
